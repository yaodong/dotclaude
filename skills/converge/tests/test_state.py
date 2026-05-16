import json
from pathlib import Path

import pytest

from converge import state


@pytest.fixture
def state_path(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    monkeypatch.setattr(state, "STATE_PATH", path)
    return path


def test_load_returns_none_when_missing(state_path):
    assert state.load() is None


def test_save_and_load_roundtrip(state_path):
    s = state.State(
        session_id="abc-123",
        round_count=3,
        started_at="2026-05-15T10:30:00Z",
        last_status="approved",
    )
    state.save(s)
    loaded = state.load()
    assert loaded == s


def test_save_creates_parent_dir(tmp_path, monkeypatch):
    nested = tmp_path / "deep" / "nested" / "state.json"
    monkeypatch.setattr(state, "STATE_PATH", nested)
    s = state.State("id", 0, "now", "approved")
    state.save(s)
    assert nested.exists()


def test_clear_removes_file(state_path):
    state.save(state.State("id", 0, "now", "approved"))
    assert state_path.exists()
    state.clear()
    assert not state_path.exists()


def test_clear_is_idempotent(state_path):
    state.clear()  # no file yet
    state.clear()  # still no file
    assert not state_path.exists()


def test_load_raises_state_corrupt_on_bad_json(state_path):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("not json {{{")
    with pytest.raises(state.StateCorrupt):
        state.load()


def test_load_raises_state_corrupt_on_missing_field(state_path):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text('{"session_id": "x"}')  # missing other fields
    with pytest.raises(state.StateCorrupt):
        state.load()


def test_load_raises_state_corrupt_on_field_type_mismatch(state_path):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"session_id": "x", "round_count": "30", "started_at": "now", "last_status": "approved"}'
    )
    with pytest.raises(state.StateCorrupt):
        state.load()


def test_load_rejects_bool_round_count(state_path):
    # bool is a subclass of int; reject explicitly so True/False can't slip through.
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        '{"session_id": "x", "round_count": true, "started_at": "now", "last_status": "approved"}'
    )
    with pytest.raises(state.StateCorrupt):
        state.load()


def test_increment_round(state_path):
    state.save(state.State("id", 5, "now", "approved"))
    new_count = state.increment_round("changes_requested")
    assert new_count == 6
    loaded = state.load()
    assert loaded.round_count == 6
    assert loaded.last_status == "changes_requested"


def test_increment_round_raises_when_no_state(state_path):
    with pytest.raises(state.NoActiveSession):
        state.increment_round("approved")
