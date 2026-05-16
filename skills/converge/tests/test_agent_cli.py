import subprocess
from unittest.mock import MagicMock

import pytest

from converge import agent_cli


def _popen_mock(stdout="", stderr="", returncode=0, communicate_raises=None):
    """Build a Popen-like mock whose .communicate() returns or raises as configured."""
    mock = MagicMock()
    if communicate_raises is not None:
        mock.communicate.side_effect = communicate_raises
    else:
        mock.communicate.return_value = (stdout, stderr)
    mock.returncode = returncode
    mock.pid = 12345
    return mock


def test_check_agent_available_passes_when_on_path(mocker):
    mocker.patch("shutil.which", return_value="/usr/local/bin/agent")
    agent_cli.check_agent_available()  # does not raise


def test_check_agent_available_raises_when_missing(mocker):
    mocker.patch("shutil.which", return_value=None)
    with pytest.raises(agent_cli.AgentCliError) as excinfo:
        agent_cli.check_agent_available()
    assert "not found" in str(excinfo.value).lower()
    assert "PATH" in str(excinfo.value)


def test_create_chat_returns_session_id(mocker):
    mocker.patch("subprocess.Popen", return_value=_popen_mock(stdout="abc-123-def\n"))
    sid = agent_cli.create_chat()
    assert sid == "abc-123-def"


def test_create_chat_passes_correct_args(mocker):
    popen_mock = mocker.patch("subprocess.Popen", return_value=_popen_mock(stdout="x"))
    agent_cli.create_chat()
    args = popen_mock.call_args[0][0]
    assert args == ["agent", "create-chat"]


def test_create_chat_raises_on_nonzero(mocker):
    mocker.patch("subprocess.Popen", return_value=_popen_mock(stderr="boom", returncode=1))
    with pytest.raises(agent_cli.AgentCliError) as excinfo:
        agent_cli.create_chat()
    assert "boom" in str(excinfo.value)


def test_run_prompt_passes_correct_args(mocker):
    popen_mock = mocker.patch("subprocess.Popen", return_value=_popen_mock(stdout="reply text"))
    out = agent_cli.run_prompt("sid-1", "hello")
    assert out == "reply text"
    args = popen_mock.call_args[0][0]
    assert args == [
        "agent", "-p",
        "--mode", "ask",
        "--model", agent_cli.CURSOR_MODEL,
        "--resume", "sid-1",
        "hello",
    ]


def test_run_prompt_uses_new_session_for_process_group(mocker):
    popen_mock = mocker.patch("subprocess.Popen", return_value=_popen_mock(stdout="x"))
    agent_cli.run_prompt("sid", "p")
    kwargs = popen_mock.call_args.kwargs
    assert kwargs.get("start_new_session") is True


def test_run_prompt_returns_combined_output_on_failure(mocker):
    mocker.patch(
        "subprocess.Popen",
        return_value=_popen_mock(stdout="partial out", stderr="bad happened", returncode=2),
    )
    with pytest.raises(agent_cli.AgentCliError) as excinfo:
        agent_cli.run_prompt("sid", "p")
    msg = str(excinfo.value)
    assert "partial out" in msg
    assert "bad happened" in msg


def test_run_prompt_timeout_kills_process_group(mocker):
    timeout_exc = subprocess.TimeoutExpired(cmd=["agent"], timeout=180)
    # First .communicate() call raises TimeoutExpired; second (after kill) returns normally.
    popen_mock = _popen_mock(communicate_raises=[timeout_exc, ("", "")])
    popen_mock.communicate.side_effect = [timeout_exc, ("", "")]
    mocker.patch("subprocess.Popen", return_value=popen_mock)
    killpg_mock = mocker.patch("os.killpg")
    mocker.patch("os.getpgid", return_value=99999)

    with pytest.raises(agent_cli.AgentCliError) as excinfo:
        agent_cli.run_prompt("sid", "p")

    assert "timeout" in str(excinfo.value).lower()
    # Two killpg calls: SIGTERM, then SIGKILL after grace period.
    assert killpg_mock.call_count >= 1


def test_run_prompt_timeout_preserves_captured_output(mocker):
    initial_timeout = subprocess.TimeoutExpired(cmd=["agent"], timeout=180)
    initial_timeout.stdout = "partial output line\n"
    initial_timeout.stderr = "warning before hang\n"
    final_out = ("more stdout after term\n", "more stderr after term\n")
    popen_mock = _popen_mock()
    popen_mock.communicate.side_effect = [initial_timeout, final_out]
    mocker.patch("subprocess.Popen", return_value=popen_mock)
    mocker.patch("os.killpg")
    mocker.patch("os.getpgid", return_value=99999)

    with pytest.raises(agent_cli.AgentCliError) as excinfo:
        agent_cli.run_prompt("sid", "p")

    msg = str(excinfo.value)
    assert "partial output line" in msg
    assert "warning before hang" in msg
    assert "more stdout after term" in msg
    assert "more stderr after term" in msg


def test_run_prompt_timeout_handles_bytes_output(mocker):
    # TimeoutExpired.stdout/stderr can be bytes even when Popen has text=True.
    initial_timeout = subprocess.TimeoutExpired(cmd=["agent"], timeout=180)
    initial_timeout.stdout = b"bytes stdout\n"
    initial_timeout.stderr = b"bytes stderr\n"
    final_out = (b"more bytes out", b"more bytes err")
    popen_mock = _popen_mock()
    popen_mock.communicate.side_effect = [initial_timeout, final_out]
    mocker.patch("subprocess.Popen", return_value=popen_mock)
    mocker.patch("os.killpg")
    mocker.patch("os.getpgid", return_value=99999)

    with pytest.raises(agent_cli.AgentCliError) as excinfo:
        agent_cli.run_prompt("sid", "p")

    msg = str(excinfo.value)
    assert "bytes stdout" in msg
    assert "bytes stderr" in msg
    assert "more bytes out" in msg
    assert "more bytes err" in msg


def test_run_prompt_timeout_handles_none_output(mocker):
    # TimeoutExpired.stdout/stderr can be None if nothing was captured.
    initial_timeout = subprocess.TimeoutExpired(cmd=["agent"], timeout=180)
    initial_timeout.stdout = None
    initial_timeout.stderr = None
    final_out = (None, None)
    popen_mock = _popen_mock()
    popen_mock.communicate.side_effect = [initial_timeout, final_out]
    mocker.patch("subprocess.Popen", return_value=popen_mock)
    mocker.patch("os.killpg")
    mocker.patch("os.getpgid", return_value=99999)

    with pytest.raises(agent_cli.AgentCliError) as excinfo:
        agent_cli.run_prompt("sid", "p")

    # Should not crash; just produce a timeout message with empty output sections.
    assert "timeout" in str(excinfo.value).lower()


def test_run_prompt_raises_when_agent_not_on_path(mocker):
    mocker.patch("subprocess.Popen", side_effect=FileNotFoundError("agent"))
    with pytest.raises(agent_cli.AgentCliError) as excinfo:
        agent_cli.run_prompt("sid", "p")
    assert "not found" in str(excinfo.value).lower() or "agent" in str(excinfo.value).lower()


def test_pinned_model_constant():
    assert agent_cli.CURSOR_MODEL == "gpt-5.5-extra-high"
