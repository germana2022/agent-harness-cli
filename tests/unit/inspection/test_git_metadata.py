import io
import subprocess
import threading

from agent_harness.infrastructure.git_metadata import (
    GitMetadataReader,
    _BoundedBuffer,
    _drain_until_eof,
)

VERBS = ("symbolic-ref", "rev-parse", "status")


class FakePopen:
    def __init__(self, stdout=b"", stderr=b"", returncode=0, timeout_first_wait=False):
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)
        self.returncode = returncode
        self._timeout_first_wait = timeout_first_wait
        self.waits = 0
        self.killed = False

    def wait(self, timeout=None):
        self.waits += 1
        if self._timeout_first_wait and self.waits == 1:
            raise subprocess.TimeoutExpired(cmd="git", timeout=timeout)
        return self.returncode

    def kill(self):
        self.killed = True


def _reader(popen_factory, **kwargs):
    defaults = dict(timeout=5.0, max_status_lines=100)
    defaults.update(kwargs)
    return GitMetadataReader(popen=popen_factory, **defaults)


def _factory(stdout_map, stderr_map=None, returncode_map=None, **popen_kwargs):
    def factory(command, **kwargs):
        verb = next((v for v in VERBS if v in command), None)
        rc = (returncode_map or {}).get(verb, 0)
        return FakePopen(
            stdout=stdout_map.get(verb, b""),
            stderr=(stderr_map or {}).get(verb, b""),
            returncode=rc,
            **popen_kwargs,
        )

    return factory


def _standard_factory():
    return _factory(
        {
            "symbolic-ref": b"main\n",
            "rev-parse": b"abc1234\n",
            "status": b" M src/a.py\n?? new.py\n",
        }
    )


def _git_threads():
    return [t for t in threading.enumerate() if t.name and t.name.startswith("ah-git-")]


def test_read_success(tmp_path):
    info = _reader(_standard_factory()).read(tmp_path)
    assert info is not None
    assert info.branch == "main"
    assert info.commit == "abc1234"
    assert info.dirty is True
    assert info.tracked_count == 1
    assert info.untracked_count == 1


def test_uses_argument_arrays_and_no_shell(tmp_path):
    calls = []

    def factory(command, **kwargs):
        calls.append((command, kwargs))
        return FakePopen(stdout=b"main\n", stderr=b"")

    _reader(factory).read(tmp_path)
    for command, kwargs in calls:
        assert isinstance(command, list)
        assert command[0] == "git"
        assert "--no-optional-locks" in command
        assert any("--git-dir=" in part for part in command)
        assert any("--work-tree=" in part for part in command)
        assert kwargs.get("shell", False) is False


def test_prompt_disabled(tmp_path):
    calls = []

    def factory(command, **kwargs):
        calls.append(kwargs)
        return FakePopen(stdout=b"main\n", stderr=b"")

    _reader(factory).read(tmp_path)
    for kwargs in calls:
        env = kwargs.get("env", {})
        assert env.get("GIT_TERMINAL_PROMPT") == "0"
        assert env.get("GIT_OPTIONAL_LOCKS") == "0"


def test_detached_head(tmp_path):
    factory = _factory({"rev-parse": b"abc1234\n"}, returncode_map={"symbolic-ref": 1})
    info = _reader(factory).read(tmp_path)
    assert info is not None
    assert info.branch is None
    assert info.commit == "abc1234"


def test_git_not_installed(tmp_path):
    def factory(*args, **kwargs):
        raise OSError("git not found")

    assert _reader(factory).read(tmp_path) is None


def test_timeout_kills_and_reaps(tmp_path):
    factory = _factory({"symbolic-ref": b"main\n"}, timeout_first_wait=True)
    info = _reader(factory, timeout=2.0).read(tmp_path)
    assert info is None


def test_timeout_process_terminated(tmp_path):
    popens = []

    def factory(command, **kwargs):
        popen = FakePopen(stdout=b"", stderr=b"", timeout_first_wait=True)
        popens.append(popen)
        return popen

    assert _reader(factory, timeout=2.0).read(tmp_path) is None
    assert all(p.killed for p in popens)
    assert all(p.waits >= 2 for p in popens)


def test_nonzero_exit(tmp_path):
    factory = _factory({}, returncode_map={v: 128 for v in VERBS})
    assert _reader(factory).read(tmp_path) is None


def test_oversized_status_line_cap(tmp_path):
    factory = _factory(
        {
            "symbolic-ref": b"main\n",
            "rev-parse": b"c\n",
            "status": "\n".join(f"?? f{i}" for i in range(500)).encode(),
        }
    )
    reader = GitMetadataReader(popen=factory, timeout=5.0, max_status_lines=100)
    info = reader.read(tmp_path)
    assert info is not None
    assert (info.untracked_count or 0) <= 100


def test_clean_repo(tmp_path):
    factory = _factory({"symbolic-ref": b"main\n", "rev-parse": b"c\n", "status": b""})
    info = _reader(factory).read(tmp_path)
    assert info.dirty is False
    assert info.tracked_count == 0
    assert info.untracked_count == 0


def test_status_failure_keeps_other_fields(tmp_path):
    factory = _factory(
        {"symbolic-ref": b"main\n", "rev-parse": b"abc\n"},
        returncode_map={"status": 1},
    )
    info = _reader(factory).read(tmp_path)
    assert info.branch == "main"
    assert info.commit == "abc"
    assert info.dirty is None
    assert info.tracked_count is None
    assert info.untracked_count is None


def test_stdout_at_limit_ok(tmp_path):
    factory = _factory(
        {"symbolic-ref": b"main\n", "rev-parse": b"c\n", "status": b"?? x\n" * 128},
    )
    info = _reader(factory, max_stdout_bytes=1024, max_status_lines=1000).read(tmp_path)
    assert info is not None
    assert (info.untracked_count or 0) == 128


def test_stdout_over_limit_unavailable(tmp_path):
    factory = _factory(
        {"symbolic-ref": b"main\n", "rev-parse": b"c\n", "status": b"?? x\n" * 4096},
    )
    info = _reader(factory, max_stdout_bytes=1024).read(tmp_path)
    assert info is None


def test_stderr_over_limit_unavailable(tmp_path):
    factory = _factory(
        {"symbolic-ref": b"main\n", "rev-parse": b"c\n", "status": b"?? x\n"},
        stderr_map={"status": b"x" * 4096},
    )
    info = _reader(factory, max_stderr_bytes=256).read(tmp_path)
    assert info is None


def test_concurrent_stdout_and_stderr_no_deadlock(tmp_path):
    factory = _factory(
        {
            "symbolic-ref": b"main\n",
            "rev-parse": b"c\n",
            "status": "".join(f"?? f{i}\n" for i in range(2000)).encode(),
        },
        stderr_map={"status": (b"a" * 40 + b"\n") * 300},
    )
    info = _reader(factory, max_stdout_bytes=64 * 1024).read(tmp_path)
    assert info is not None
    assert (info.untracked_count or 0) > 0


def test_no_leaked_threads_after_read(tmp_path):
    factory = _standard_factory()
    _reader(factory).read(tmp_path)
    assert _git_threads() == []


def test_truncation_deterministic(tmp_path):
    factory = _factory(
        {"symbolic-ref": b"main\n", "rev-parse": b"c\n", "status": b"?? x\n" * 4096},
    )
    reader = _reader(factory, max_stdout_bytes=1024)
    assert reader.read(tmp_path) is None
    assert reader.read(tmp_path) is None


def test_normal_behavior_unchanged_large_below_bound(tmp_path):
    factory = _factory(
        {"symbolic-ref": b"main\n", "rev-parse": b"c\n", "status": b"?? f\n" * 500},
    )
    info = _reader(factory, max_stdout_bytes=1024 * 1024, max_status_lines=1000).read(tmp_path)
    assert info is not None
    assert info.untracked_count == 500


def test_bounded_buffer_limits():
    buf = _BoundedBuffer(4)
    buf.feed(b"abcd")
    assert buf.truncated is False
    assert buf.size == 4
    buf.feed(b"efghijkl")
    assert buf.truncated is True
    assert buf.size == 4
    buf.feed(b"m")
    assert buf.size == 4


def test_bounded_buffer_exact_half_chunk():
    buf = _BoundedBuffer(4)
    buf.feed(b"abcdef")
    assert buf.truncated is True
    assert buf.to_bytes() == b"abcd"


def test_bounded_buffer_zero_limit():
    buf = _BoundedBuffer(0)
    buf.feed(b"x")
    assert buf.truncated is True
    assert buf.to_bytes() == b""


class FailingReadStream:
    def read(self, size=-1):
        raise ValueError("pipe closed")

    def close(self):
        pass


def test_drain_tolerates_read_error():
    buf = _BoundedBuffer(10)
    _drain_until_eof(FailingReadStream(), buf)
    assert buf.to_bytes() == b""
    assert buf.truncated is False


class FailingCloseStream:
    def __init__(self):
        self.reads = 0

    def read(self, size=-1):
        self.reads += 1
        return b"x" if self.reads == 1 else b""

    def close(self):
        raise OSError("boom")


def test_drain_tolerates_close_error():
    buf = _BoundedBuffer(10)
    _drain_until_eof(FailingCloseStream(), buf)
    assert buf.to_bytes() == b"x"
    assert buf.truncated is False


class BlockingStream:
    """A read stream that blocks until explicitly closed, simulating a child
    that keeps a pipe open past the process exit."""

    def __init__(self):
        self._released = threading.Event()

    def read(self, size=-1):
        self._released.wait(15.0)
        return b""

    def close(self):
        self._released.set()
        raise OSError("close failed")


class SlowPopen:
    def __init__(self):
        self.stdout = BlockingStream()
        self.stderr = BlockingStream()
        self.returncode = 0

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


def test_cleanup_forces_pipe_close_and_joins(tmp_path):
    reader = GitMetadataReader(popen=lambda *a, **k: SlowPopen(), timeout=0.001)
    captured = reader._capture(["git"], cwd=str(tmp_path), env={})
    assert captured is not None
    assert all(not t.is_alive() for t in _git_threads())