from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .model import Check, Report, Severity

MAX_SCAN_BYTES = 2 * 1024 * 1024
LARGE_FILE_BYTES = 5 * 1024 * 1024
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\baws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{16,}"),
    re.compile(r"(?i)\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)\b(?:xai|hf|pplx|r8|AIza)[_-][A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)\b(?:openai|anthropic|gemini|azure_openai|ollama)_[A-Za-z0-9_]*key\s*[:=]"),
)
ACTION_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
ACTION_USE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")


def scan(root: str | Path = ".", *, strict_workflow_pins: bool = False) -> Report:
    path = Path(root).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"not a directory: {path}")

    tracked = _git_files(path)
    files = _all_files(path)
    checks = [
        _documentation_check(path),
        _license_check(path),
        _contributing_check(path),
        _security_policy_check(path),
        _code_of_conduct_check(path),
        _ci_check(path),
        _workflow_pin_check(path, strict_workflow_pins),
        _ignore_check(path),
        _tests_check(path),
        _metadata_check(path),
        _git_check(path, tracked),
        _secret_check(path, tracked),
        _large_file_check(path, tracked),
    ]
    large = tuple(_large_files(path, tracked))
    secrets = tuple(_secret_files(path, tracked))
    branch = _git_output(path, ["branch", "--show-current"]) or None
    dirty = bool(_git_output(path, ["status", "--porcelain"]))
    return Report(path, tuple(checks), len(files), len(tracked), large, secrets, dirty, branch)


def _workflow_pin_check(root: Path, strict: bool) -> Check:
    workflow_dir = root / ".github" / "workflows"
    workflows = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml")) if workflow_dir.is_dir() else []
    if not workflows:
        return Check("workflow-pins", "Workflow action pins", Severity.INFO, 0, "no workflow files found")

    unpinned: list[str] = []
    for workflow in workflows:
        try:
            lines = workflow.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, 1):
            if line.lstrip().startswith("#"):
                continue
            match = ACTION_USE.match(line)
            if not match:
                continue
            action = match.group(1).strip().strip('"\'')
            if action.startswith(("./", "docker://")):
                continue
            ref = action.rsplit("@", 1)[-1] if "@" in action else ""
            if not ACTION_SHA.fullmatch(ref):
                unpinned.append(f"{workflow.relative_to(root)}:{line_number} ({action})")

    if not unpinned:
        return Check("workflow-pins", "Workflow action pins", Severity.PASS, 2, "third-party actions are pinned to commit SHAs")
    level = Severity.FAIL if strict else Severity.INFO
    message = "unpinned workflow actions: " + ", ".join(unpinned[:3])
    if len(unpinned) > 3:
        message += f" (+{len(unpinned) - 3} more)"
    suggestion = "Pin each third-party action to a full 40-character commit SHA and document the release tag in a comment."
    return Check("workflow-pins", "Workflow action pins", level, 0, message, suggestion)


def _documentation_check(root: Path) -> Check:
    readme = _first(root, "README.md", "README.rst", "README.txt", "README")
    if readme:
        return Check("readme", "README", Severity.PASS, 2, f"found {readme.name}")
    return Check("readme", "README", Severity.FAIL, 0, "no README file found", "Add a README with setup and usage instructions.")


def _license_check(root: Path) -> Check:
    license_file = _first(root, "LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
    if license_file:
        return Check("license", "License", Severity.PASS, 2, f"found {license_file.name}")
    return Check("license", "License", Severity.WARN, 1, "no license file found", "Choose a license so others know how they may reuse the project.")


def _contributing_check(root: Path) -> Check:
    paths = (root / "CONTRIBUTING.md", root / ".github" / "CONTRIBUTING.md", root / "docs" / "CONTRIBUTING.md")
    if any(path.is_file() for path in paths):
        return Check("contributing", "Contribution guide", Severity.PASS, 2, "contribution instructions are present")
    return Check("contributing", "Contribution guide", Severity.INFO, 0, "no contribution guide", "Add one when you want outside contributions.")


def _security_policy_check(root: Path) -> Check:
    paths = (root / "SECURITY.md", root / ".github" / "SECURITY.md", root / "docs" / "SECURITY.md")
    if any(path.is_file() for path in paths):
        return Check("security", "Security policy", Severity.PASS, 2, "security policy is present")
    return Check("security", "Security policy", Severity.WARN, 1, "no security policy", "Add SECURITY.md with a private reporting path.")


def _code_of_conduct_check(root: Path) -> Check:
    paths = (root / "CODE_OF_CONDUCT.md", root / ".github" / "CODE_OF_CONDUCT.md", root / "docs" / "CODE_OF_CONDUCT.md")
    if any(path.is_file() for path in paths):
        return Check("conduct", "Code of conduct", Severity.PASS, 2, "code of conduct is present")
    return Check("conduct", "Code of conduct", Severity.INFO, 0, "no code of conduct", "Add one if the project accepts community contributions.")


def _ci_check(root: Path) -> Check:
    workflow_dir = root / ".github" / "workflows"
    workflows = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml")) if workflow_dir.is_dir() else []
    if workflows:
        return Check("ci", "Continuous integration", Severity.PASS, 2, f"found {len(workflows)} workflow(s)")
    return Check("ci", "Continuous integration", Severity.WARN, 1, "no GitHub Actions workflow found", "Add a workflow that runs tests on pull requests.")


def _ignore_check(root: Path) -> Check:
    if (root / ".gitignore").is_file():
        return Check("gitignore", "Ignore rules", Severity.PASS, 2, "found .gitignore")
    return Check("gitignore", "Ignore rules", Severity.WARN, 1, "no .gitignore found", "Ignore build output, local environments, and secrets.")


def _tests_check(root: Path) -> Check:
    names = ("tests", "test", "__tests__", "src/test", "src/tests")
    if any((root / name).is_dir() for name in names):
        return Check("tests", "Tests", Severity.PASS, 2, "test directory found")
    if any(next(root.glob(pattern), None) is not None for pattern in ("**/*Test.java", "**/*_test.py", "**/*.spec.ts", "**/*.test.js")):
        return Check("tests", "Tests", Severity.PASS, 2, "test files found")
    return Check("tests", "Tests", Severity.WARN, 1, "no obvious test directory or test file", "Add a small regression test suite before publishing.")


def _metadata_check(root: Path) -> Check:
    metadata = ("pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts")
    found = [name for name in metadata if (root / name).is_file()]
    if found:
        return Check("metadata", "Project metadata", Severity.PASS, 2, "found " + ", ".join(found))
    return Check("metadata", "Project metadata", Severity.INFO, 0, "no common package metadata found", "Add package metadata if this repository is a distributable project.")


def _git_check(root: Path, tracked: list[str]) -> Check:
    if not (root / ".git").exists():
        return Check("git", "Git repository", Severity.INFO, 0, "not a Git worktree", "Run the check from a Git repository for branch and tracked-file checks.")
    if not tracked:
        return Check("git", "Git repository", Severity.WARN, 1, "Git repository has no tracked files")
    return Check("git", "Git repository", Severity.PASS, 2, f"{len(tracked)} tracked file(s)")


def _secret_check(root: Path, tracked: list[str]) -> Check:
    matches = _secret_files(root, tracked)
    if matches:
        return Check("secrets", "Secret scan", Severity.FAIL, 0, "possible secret material in " + ", ".join(matches[:3]), "Remove the secret, rotate it, and add the file to .gitignore.")
    return Check("secrets", "Secret scan", Severity.PASS, 2, "no common private-key or token patterns found")


def _large_file_check(root: Path, tracked: list[str]) -> Check:
    large = _large_files(root, tracked)
    if large:
        return Check("large-files", "Large files", Severity.WARN, 1, f"{len(large)} tracked file(s) exceed 5 MiB", "Use Git LFS or release assets for large binaries.")
    return Check("large-files", "Large files", Severity.PASS, 2, "no tracked file exceeds 5 MiB")


def _all_files(root: Path) -> list[Path]:
    ignored = {".git", ".venv", "node_modules", "target", "dist", "build", "__pycache__"}
    return [path for path in root.rglob("*") if path.is_file() and not ignored.intersection(path.relative_to(root).parts)]


def _git_files(root: Path) -> list[str]:
    output = _git_output(root, ["ls-files", "-z"])
    return output.split("\0")[:-1] if output else []


def _large_files(root: Path, tracked: list[str]) -> list[str]:
    result = []
    for relative in tracked:
        path = root / relative
        try:
            if path.stat().st_size > LARGE_FILE_BYTES:
                result.append(relative)
        except OSError:
            continue
    return result


def _secret_files(root: Path, tracked: list[str]) -> list[str]:
    result = []
    for relative in tracked:
        path = root / relative
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            result.append(relative)
    return result


def _first(root: Path, *names: str) -> Path | None:
    for name in names:
        path = root / name
        if path.is_file():
            return path
    return None


def _git_output(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, check=False, capture_output=True, text=True)
    except OSError:
        return ""
    return result.stdout.strip("\n") if result.returncode == 0 else ""
