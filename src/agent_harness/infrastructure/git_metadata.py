"""Read-only local Git metadata adapter.

Executes only non-mutating, local Git commands using argument arrays. It never
fetches, never contacts remotes, never queries credential helpers, and never
modifies repository state. A timeout and bounded stdout/stderr capture are
enforced while bytes are being received, and all prompting is disabled.
"""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..inspection.result import GitInfo

PopenFactory = Callable[..., subprocess.Popen]

_COMMON_GIT_ARGS = ("--no-optional-locks",)
_MAX_READ_CHUNK = 64 * 1024

# Sentinel distinguishing "output exceeded its explicit byte limit" from other
# process failures, so callers can report a stable truncation outcome.
_TRUNCATED = object()


class _BoundedBuffer:
    """Byte buffer that stops retaining bytes once a hard limit is reached.

    ``feed`` keeps at most ``limit`` bytes and sets ``truncated`` once the limit
    would be exceeded. Dropped bytes are never retained, so memory stays bounded
    regardless of how much the child writes.
    """

    __slots__ = ("_limit", "_data", "truncated")

    def __init__(self, limit: int) -> None:
        self._limit = max(0, limit)
        self._data = bytearray()
        self.truncated = False

    def feed(self, chunk: bytes) -> None:
        if self.truncated:
            return
        room = self._limit - len(self._data)
        if room <= 0:
            self.truncated = True
            return
        if len(chunk) > room:
            self._data += chunk[:room]
            self.truncated = True
        else:
            self._data += chunk

    @property
    def size(self) -> int:
        return len(self._data)

    def to_bytes(self) -> bytes:
        return bytes(self._data)


def _drain_until_eof(stream, buffer: _BoundedBuffer) -> None:
    """Drain a child pipe to EOF without blocking the writer.

    When the buffer is full, remaining bytes are read and discarded so the child
    never blocks on a full pipe (which would deadlock the process). Exceptions
    from a forcibly closed pipe terminate the drain cleanly.
    """
    try:
        while True:
            try:
                chunk = stream.read(_MAX_READ_CHUNK)
            except (OSError, ValueError):
                return
            if not chunk:
                return
            buffer.feed(chunk)
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass


@dataclass(frozen=True)
class GitMetadataReader:
    popen: PopenFactory = field(default_factory=lambda: subprocess.Popen)
    timeout: float = 5.0
    max_status_lines: int = 10_000
    max_stdout_bytes: int = 1_048_576
    max_stderr_bytes: int = 65_536

    def read(self, repo_root: Path) -> GitInfo | None:
        """Return bounded Git metadata, or ``None`` when unavailable.

        Output that exceeds the explicit byte limits is discarded and reported
        as unavailable (a deterministic, sanitized ``GIT_METADATA_UNAVAILABLE``
        result) rather than captured without bound.
        """
        branch, branch_truncated = self._run(
            repo_root, ("symbolic-ref", "--quiet", "--short", "HEAD")
        )
        commit, commit_truncated = self._run(repo_root, ("rev-parse", "--short", "HEAD"))
        status, status_truncated = self._run(
            repo_root, ("status", "--porcelain", "--untracked-files=all")
        )
        if branch_truncated or commit_truncated or status_truncated:
            return None
        if branch is None and commit is None and status is None:
            return None
        branch_value = None if branch is None else _clean_line(branch)
        commit_value = None if commit is None else _clean_line(commit)
        tracked = None
        untracked = None
        dirty = None
        if status is not None:
            lines = [line for line in status.splitlines()[: self.max_status_lines] if line]
            tracked = 0
            untracked = 0
            for line in lines:
                if line.startswith("??"):
                    untracked += 1
                else:
                    tracked += 1
            dirty = len(lines) > 0
        return GitInfo(
            branch=branch_value,
            commit=commit_value,
            dirty=dirty,
            tracked_count=tracked,
            untracked_count=untracked,
        )

    def _run(self, repo_root: Path, args: tuple[str, ...]) -> tuple[str | None, bool]:
        command = [
            "git",
            *_COMMON_GIT_ARGS,
            f"--git-dir={repo_root / '.git'}",
            f"--work-tree={repo_root}",
            *args,
        ]
        captured = self._capture(command, cwd=str(repo_root), env=self._environment())
        if captured is _TRUNCATED:
            return None, True
        if captured is None:
            return None, False
        stdout_bytes, _stderr_bytes = captured
        return stdout_bytes.decode("utf-8", errors="replace"), False

    def _capture(self, command: list[str], *, cwd: str, env: dict[str, str]):
        """Run a command and collect bounded stdout/stderr.

        Returns ``(stdout_bytes, stderr_bytes)`` on success, ``_TRUNCATED`` when
        output exceeded an explicit byte limit, or ``None`` when the process
        failed or timed out. Both pipes are drained concurrently so the child
        can never block on a full pipe (no deadlock), and the process is
        terminated and reaped deterministically on timeout.
        """
        stdout_buf = _BoundedBuffer(self.max_stdout_bytes)
        stderr_buf = _BoundedBuffer(self.max_stderr_bytes)
        try:
            proc = self.popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
            )
        except OSError:
            return None
        out_thread = threading.Thread(
            target=_drain_until_eof,
            args=(proc.stdout, stdout_buf),
            name="ah-git-stdout",
            daemon=True,
        )
        err_thread = threading.Thread(
            target=_drain_until_eof,
            args=(proc.stderr, stderr_buf),
            name="ah-git-stderr",
            daemon=True,
        )
        out_thread.start()
        err_thread.start()
        timed_out = False
        try:
            proc.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
        out_thread.join(timeout=self.timeout + 5.0)
        err_thread.join(timeout=self.timeout + 5.0)
        if out_thread.is_alive() or err_thread.is_alive():
            try:
                proc.stdout.close()
            except (OSError, ValueError):
                pass
            try:
                proc.stderr.close()
            except (OSError, ValueError):
                pass
            out_thread.join()
            err_thread.join()
        if timed_out:
            return None
        if stdout_buf.truncated or stderr_buf.truncated:
            return _TRUNCATED
        if proc.returncode != 0:
            return None
        return stdout_buf.to_bytes(), stderr_buf.to_bytes()

    @staticmethod
    def _environment() -> dict[str, str]:
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_OPTIONAL_LOCKS"] = "0"
        return env


def _clean_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else value.strip()