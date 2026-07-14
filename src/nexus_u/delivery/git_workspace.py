from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
from typing import Any, Iterable


@dataclass(slots=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    category: str = "command"

    @property
    def success(self) -> bool:
        return self.returncode == 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["success"] = self.success
        return payload


@dataclass(slots=True)
class DeliveryResult:
    success: bool
    workspace: str
    base_commit: str
    diff: str
    diff_sha256: str
    commands: list[CommandResult] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "workspace": self.workspace,
            "base_commit": self.base_commit,
            "diff": self.diff,
            "diff_sha256": self.diff_sha256,
            "commands": [item.to_dict() for item in self.commands],
            "checks": self.checks,
            "obligations": self.obligations,
            "changed_files": self.changed_files,
        }


class GitWorkspaceError(RuntimeError):
    pass


def _normalize_command(command: str | Iterable[str]) -> list[str]:
    if isinstance(command, str):
        return shlex.split(command)
    return [str(part) for part in command]


class GitWorkspace:
    """Disposable Git-backed workspace for trusted local delivery tasks.

    The source repository is never modified. A local clone is created in a
    temporary directory, changes are applied, and declared commands are run with
    explicit timeouts. This is not a security sandbox for hostile code.
    """

    def __init__(self, source: str | Path, *, timeout: float = 60.0) -> None:
        self.source = Path(source).resolve()
        self.timeout = timeout
        self._tmp = Path(tempfile.mkdtemp(prefix="nexus-u-reality-"))
        self.path = self._tmp / "repo"
        self._prepared = False
        self.base_commit = ""

    def prepare(self) -> None:
        if not self.source.exists() or not self.source.is_dir():
            raise GitWorkspaceError(f"Repository path does not exist: {self.source}")
        git = shutil.which("git")
        if not git:
            raise GitWorkspaceError("git executable is unavailable")
        source_git = self.source / ".git"
        if source_git.exists():
            proc = subprocess.run(
                [git, "clone", "--quiet", "--no-hardlinks", str(self.source), str(self.path)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            if proc.returncode != 0:
                raise GitWorkspaceError(f"git clone failed: {proc.stderr.strip()}")
        else:
            shutil.copytree(self.source, self.path)
            self._git(["init", "--quiet"])
            self._git(["config", "user.email", "nexus-u@example.invalid"])
            self._git(["config", "user.name", "NEXUS-U"])
            self._git(["add", "-A"])
            self._git(["commit", "--quiet", "-m", "fixture baseline"])
        self.base_commit = self._git(["rev-parse", "HEAD"]).stdout.strip()
        self._prepared = True

    def _git(self, args: list[str], *, check: bool = True) -> CommandResult:
        started = time.monotonic()
        proc = subprocess.run(
            ["git", *args],
            cwd=self.path,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        result = CommandResult(["git", *args], proc.returncode, proc.stdout, proc.stderr, time.monotonic() - started, "git")
        if check and not result.success:
            raise GitWorkspaceError(result.stderr.strip() or f"git {' '.join(args)} failed")
        return result

    def apply_changes(self, *, files: dict[str, str] | None = None, patch: str | None = None) -> None:
        if not self._prepared:
            self.prepare()
        for relative, content in (files or {}).items():
            target = (self.path / relative).resolve()
            try:
                target.relative_to(self.path.resolve())
            except ValueError as exc:
                raise GitWorkspaceError(f"Change escapes repository: {relative}") from exc
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        if patch:
            patch_path = self._tmp / "candidate.patch"
            patch_path.write_text(patch, encoding="utf-8")
            self._git(["apply", "--whitespace=error", str(patch_path)])

    def run_command(self, command: str | Iterable[str], *, category: str = "command", timeout: float | None = None) -> CommandResult:
        argv = _normalize_command(command)
        if not argv:
            raise GitWorkspaceError("Empty command")
        started = time.monotonic()
        try:
            proc = subprocess.run(
                argv,
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                check=False,
                env={"PATH": str(Path(shutil.which(argv[0]) or "").parent) + ":/usr/local/bin:/usr/bin:/bin", "PYTHONHASHSEED": "0"},
            )
            return CommandResult(argv, proc.returncode, proc.stdout, proc.stderr, time.monotonic() - started, category)
        except FileNotFoundError as exc:
            return CommandResult(argv, 127, "", str(exc), time.monotonic() - started, category)
        except subprocess.TimeoutExpired as exc:
            return CommandResult(argv, 124, exc.stdout or "", exc.stderr or "command timed out", time.monotonic() - started, category)

    def diff(self) -> str:
        return self._git(["diff", "--binary", "HEAD"], check=False).stdout

    def changed_files(self) -> list[str]:
        output = self._git(["status", "--porcelain"], check=False).stdout
        return [line[3:] for line in output.splitlines() if len(line) > 3]

    def inspect(
        self,
        *,
        required_paths: Iterable[str] = (),
        forbidden_patterns: Iterable[dict[str, str]] = (),
        required_patterns: Iterable[dict[str, str]] = (),
    ) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        for relative in required_paths:
            exists = (self.path / relative).exists()
            checks.append({"kind": "required_path", "target": relative, "success": exists})
        for item in forbidden_patterns:
            relative = str(item.get("path", ""))
            pattern = str(item.get("pattern", ""))
            path = self.path / relative
            text = path.read_text(encoding="utf-8") if path.exists() and path.is_file() else ""
            checks.append({"kind": "forbidden_pattern", "target": relative, "pattern": pattern, "success": pattern not in text})
        for item in required_patterns:
            relative = str(item.get("path", ""))
            pattern = str(item.get("pattern", ""))
            path = self.path / relative
            text = path.read_text(encoding="utf-8") if path.exists() and path.is_file() else ""
            checks.append({"kind": "required_pattern", "target": relative, "pattern": pattern, "success": pattern in text})
        return checks

    def execute_delivery(
        self,
        *,
        changes: dict[str, str] | None = None,
        patch: str | None = None,
        command_groups: dict[str, list[str | list[str]]] | None = None,
        required_paths: Iterable[str] = (),
        forbidden_patterns: Iterable[dict[str, str]] = (),
        required_patterns: Iterable[dict[str, str]] = (),
        rollback_required: bool = False,
        rollback_command: str | list[str] | None = None,
    ) -> DeliveryResult:
        self.prepare()
        self.apply_changes(files=changes, patch=patch)
        results: list[CommandResult] = []
        obligations: list[str] = []
        for category, commands in (command_groups or {}).items():
            for command in commands:
                result = self.run_command(command, category=category)
                results.append(result)
                if not result.success:
                    obligations.append(f"{category} command failed: {' '.join(result.command)}")
        checks = self.inspect(required_paths=required_paths, forbidden_patterns=forbidden_patterns, required_patterns=required_patterns)
        for check in checks:
            if not check["success"]:
                obligations.append(f"{check['kind']} failed for {check['target']}")
        if rollback_required and not rollback_command:
            checks.append({"kind": "rollback", "target": "rollback_command", "success": False})
            obligations.append("Rollback command is required but missing")
        elif rollback_command:
            # Validate syntax and executable availability without executing destructive rollback.
            argv = _normalize_command(rollback_command)
            executable = shutil.which(argv[0]) if argv else None
            ok = bool(argv and executable)
            checks.append({"kind": "rollback", "target": " ".join(argv), "success": ok})
            if not ok:
                obligations.append("Rollback command is not executable")
        diff = self.diff()
        changed = self.changed_files()
        if not diff and not changed:
            obligations.append("Candidate produced no Git change")
        return DeliveryResult(
            success=not obligations,
            workspace=str(self.path),
            base_commit=self.base_commit,
            diff=diff,
            diff_sha256=hashlib.sha256(diff.encode()).hexdigest(),
            commands=results,
            checks=checks,
            obligations=obligations,
            changed_files=changed,
        )

    def write_snapshot(self, path: str | Path) -> Path:
        payload = {
            "source": str(self.source),
            "workspace": str(self.path),
            "base_commit": self.base_commit,
            "diff_sha256": hashlib.sha256(self.diff().encode()).hexdigest(),
            "changed_files": self.changed_files(),
        }
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return output

    def cleanup(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
