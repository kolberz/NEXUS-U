from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    safe_env = dict(os.environ)
    safe_env.update({"PYTHONHASHSEED": "0", "NO_COLOR": "1"})
    if env:
        safe_env.update(env)
    try:
        proc = subprocess.run(
            list(command),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env,
            check=False,
        )
        return CommandResult(tuple(command), proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            tuple(command),
            124,
            exc.stdout or "",
            exc.stderr or "",
            timed_out=True,
        )
