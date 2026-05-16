from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from converge import agent_cli, server, state


@pytest.fixture
def no_active_session(mocker):
    mocker.patch("converge.server.state.load", return_value=None)


@pytest.fixture
def active_session(mocker):
    s = state.State("existing-id", 5, "2026-05-15T10:00:00Z", "approved")
    mocker.patch("converge.server.state.load", return_value=s)
    return s


@pytest.fixture
def corrupt_state(mocker):
    mocker.patch(
        "converge.server.state.load",
        side_effect=state.StateCorrupt("bad json"),
    )


# ----- converge.start -----

def test_start_returns_error_if_session_active(active_session):
    out = server.start_impl("topic")
    assert out["ok"] is False
    assert out["reason"] == "session_active"
    assert out["session_id"] == "existing-id"


def test_start_returns_error_on_corrupt_state(corrupt_state, mocker):
    create_mock = mocker.patch("converge.server.agent_cli.create_chat")
    out = server.start_impl("topic")
    assert out["ok"] is False
    assert out["reason"] == "state_corrupt"
    create_mock.assert_not_called()


def test_start_creates_chat_and_seeds_when_no_session(no_active_session, mocker):
    mocker.patch("converge.server.agent_cli.create_chat", return_value="new-uuid")
    mocker.patch(
        "converge.server.agent_cli.run_prompt",
        return_value="Acknowledged.\n\nSTATUS: APPROVED",
    )
    save_mock = mocker.patch("converge.server.state.save")

    out = server.start_impl("auth refactor")

    assert out["ok"] is True
    assert out["session_id"] == "new-uuid"
    save_mock.assert_called_once()
    saved_state = save_mock.call_args[0][0]
    assert saved_state.session_id == "new-uuid"
    assert saved_state.round_count == 0
    assert saved_state.last_status == "approved"


def test_start_does_not_persist_when_seed_not_acknowledged(no_active_session, mocker):
    mocker.patch("converge.server.agent_cli.create_chat", return_value="new-uuid")
    mocker.patch(
        "converge.server.agent_cli.run_prompt",
        return_value="I am confused.\n\nSTATUS: CHANGES_REQUESTED",
    )
    save_mock = mocker.patch("converge.server.state.save")

    out = server.start_impl("topic")

    assert out["ok"] is False
    assert out["reason"] == "seed_not_acknowledged"
    save_mock.assert_not_called()


# ----- converge.iterate -----

def test_iterate_no_session_returns_no_session(no_active_session):
    out = server.iterate_impl("hi", [])
    assert out["status"] == "no_session"


def test_iterate_at_cap_rejects_without_running_agent(mocker):
    s = state.State("id", 30, "now", "approved")
    mocker.patch("converge.server.state.load", return_value=s)
    run_mock = mocker.patch("converge.server.agent_cli.run_prompt")

    out = server.iterate_impl("hi", [])

    assert out["status"] == "limit_reached"
    assert out["round"] == 30
    run_mock.assert_not_called()


def test_iterate_runs_agent_parses_status_increments(mocker):
    s = state.State("id", 5, "now", "approved")
    mocker.patch("converge.server.state.load", return_value=s)
    mocker.patch(
        "converge.server.agent_cli.run_prompt",
        return_value="critique\n\nSTATUS: CHANGES_REQUESTED",
    )
    incr_mock = mocker.patch(
        "converge.server.state.increment_round", return_value=6
    )

    out = server.iterate_impl("review please", ["/abs/spec.md"])

    assert out["status"] == "changes_requested"
    assert out["round"] == 6
    incr_mock.assert_called_once_with("changes_requested")


def test_iterate_passes_formatted_prompt_to_agent(mocker):
    s = state.State("sid-1", 0, "now", "approved")
    mocker.patch("converge.server.state.load", return_value=s)
    run_mock = mocker.patch(
        "converge.server.agent_cli.run_prompt",
        return_value="ok\n\nSTATUS: APPROVED",
    )
    mocker.patch("converge.server.state.increment_round", return_value=1)

    server.iterate_impl("review", ["/x/spec.md"])

    args, _ = run_mock.call_args
    assert args[0] == "sid-1"
    assert "review" in args[1]
    assert "Contexts:" in args[1]
    assert "/x/spec.md" in args[1]


def test_iterate_agent_failure_increments_and_returns_error(mocker):
    s = state.State("id", 5, "now", "approved")
    mocker.patch("converge.server.state.load", return_value=s)
    mocker.patch(
        "converge.server.agent_cli.run_prompt",
        side_effect=agent_cli.AgentCliError("boom"),
    )
    incr_mock = mocker.patch(
        "converge.server.state.increment_round", return_value=6
    )

    out = server.iterate_impl("m", [])

    assert out["status"] == "error"
    assert "boom" in out["reply"]
    assert out["round"] == 6
    # Errors still count against the cap.
    incr_mock.assert_called_once_with("error")


# ----- converge.status -----

def test_status_no_session(no_active_session):
    out = server.status_impl()
    assert out["ok"] is False
    assert out["reason"] == "no_session"


def test_status_returns_state_and_transcript(active_session, mocker):
    mocker.patch(
        "converge.server.transcript.find_transcript",
        return_value=("/cursor/path.jsonl", None),
    )
    out = server.status_impl()
    assert out["ok"] is True
    assert out["session_id"] == "existing-id"
    assert out["round_count"] == 5
    assert out["last_status"] == "approved"
    assert out["transcript_path"] == "/cursor/path.jsonl"
    assert out["transcript_note"] is None


def test_status_handles_missing_transcript(active_session, mocker):
    mocker.patch(
        "converge.server.transcript.find_transcript",
        return_value=(None, "transcript file not found at known locations"),
    )
    out = server.status_impl()
    assert out["transcript_path"] is None
    assert "not found" in out["transcript_note"]


# ----- converge.end -----

def test_end_clears_state_when_active(active_session, mocker):
    clear_mock = mocker.patch("converge.server.state.clear")
    out = server.end_impl()
    assert out["ok"] is True
    assert out["ended_session_id"] == "existing-id"
    clear_mock.assert_called_once()


def test_end_idempotent_when_no_session(no_active_session, mocker):
    clear_mock = mocker.patch("converge.server.state.clear")
    out = server.end_impl()
    assert out["ok"] is True
    assert out["no_session"] is True
    clear_mock.assert_called_once()  # idempotent: still safe to call


# ----- corruption handling -----

def test_iterate_returns_error_on_corrupt_state(corrupt_state):
    out = server.iterate_impl("hi", [])
    assert out["status"] == "error"
    assert "corrupt" in out["reply"].lower()


def test_status_returns_error_on_corrupt_state(corrupt_state):
    out = server.status_impl()
    assert out["ok"] is False
    assert out["reason"] == "state_corrupt"


def test_end_clears_corrupt_state(corrupt_state, mocker):
    clear_mock = mocker.patch("converge.server.state.clear")
    out = server.end_impl()
    assert out["ok"] is True
    assert out["cleared_corrupt_state"] is True
    clear_mock.assert_called_once()
