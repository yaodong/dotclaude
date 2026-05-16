"""Wrapper around the Cursor `agent` CLI."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess

CURSOR_MODEL = "gpt-5.5-extra-high"
TIMEOUT_SECONDS = 180
SIGKILL_GRACE_SECONDS = 5


class AgentCliError(Exception):
    """Raised when the `agent` CLI is missing, exits non-zero, times out, etc."""


def _decode(value: str | bytes | None) -> str:
    """Normalize subprocess output to str. TimeoutExpired.stdout/stderr can be
    bytes even with text=True, and may be None if nothing was captured.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def check_agent_available() -> None:
    """Raise AgentCliError if `agent` is not on PATH. Called at server startup."""
    if shutil.which("agent") is None:
        raise AgentCliError(
            "`agent` CLI not found on PATH. Install Cursor's agent CLI: "
            "https://docs.cursor.com/agent/cli"
        )


def _run(cmd: list[str]) -> str:
    """Run a command in its own process group, with timeout and group-kill on timeout.

    Returns stdout on success. Raises AgentCliError on missing binary, non-zero exit,
    or timeout. On timeout, sends SIGTERM to the entire process group, waits up to
    SIGKILL_GRACE_SECONDS, then sends SIGKILL.
    """
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # creates a new process group; the agent
            # CLI is a Node binary that may spawn workers/children.
        )
    except FileNotFoundError as e:
        raise AgentCliError(f"`agent` not found: {e}") from e

    try:
        stdout, stderr = proc.communicate(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as initial_timeout:
        # Spec: SIGTERM then SIGKILL after 5s. Preserve any output captured
        # before/during shutdown so the caller gets diagnostic context.
        # Note: TimeoutExpired.stdout/stderr can be bytes even when Popen was
        # opened with text=True, and may be None if no output was captured.
        # _decode handles both cases.
        captured_stdout = _decode(initial_timeout.stdout)
        captured_stderr = _decode(initial_timeout.stderr)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            late_out, late_err = proc.communicate(timeout=SIGKILL_GRACE_SECONDS)
            captured_stdout += _decode(late_out)
            captured_stderr += _decode(late_err)
        except subprocess.TimeoutExpired as grace_timeout:
            captured_stdout += _decode(grace_timeout.stdout)
            captured_stderr += _decode(grace_timeout.stderr)
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                late_out, late_err = proc.communicate(timeout=1)
                captured_stdout += _decode(late_out)
                captured_stderr += _decode(late_err)
            except subprocess.TimeoutExpired as kill_timeout:
                captured_stdout += _decode(kill_timeout.stdout)
                captured_stderr += _decode(kill_timeout.stderr)
        raise AgentCliError(
            f"agent timeout after {TIMEOUT_SECONDS}s; process group killed\n"
            f"stdout: {captured_stdout.strip()}\n"
            f"stderr: {captured_stderr.strip()}"
        ) from None

    if proc.returncode != 0:
        raise AgentCliError(
            f"agent failed (exit {proc.returncode})\n"
            f"stdout: {stdout.strip()}\n"
            f"stderr: {stderr.strip()}"
        )
    return stdout


def create_chat() -> str:
    """Run `agent create-chat`. Returns the new session ID (stripped)."""
    return _run(["agent", "create-chat"]).strip()


def run_prompt(session_id: str, prompt: str) -> str:
    """Run `agent -p --resume <id> "<prompt>"`. Returns stdout."""
    cmd = [
        "agent", "-p",
        "--mode", "ask",
        "--model", CURSOR_MODEL,
        "--resume", session_id,
        prompt,
    ]
    return _run(cmd)
