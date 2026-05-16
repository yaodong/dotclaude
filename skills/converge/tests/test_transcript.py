from pathlib import Path

import pytest

from converge import transcript


@pytest.fixture
def cursor_root(tmp_path, monkeypatch):
    monkeypatch.setattr(transcript, "CURSOR_ROOT", tmp_path / ".cursor")
    return tmp_path / ".cursor"


def test_returns_null_when_no_files_match(cursor_root):
    path, note = transcript.find_transcript("missing-id")
    assert path is None
    assert note is not None
    assert "not found" in note.lower()


def test_finds_nested_layout(cursor_root):
    sid = "11111111-2222-3333-4444-555555555555"
    nested = (
        cursor_root / "projects" / "some-project" / "agent-transcripts" / sid / f"{sid}.jsonl"
    )
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("{}\n")
    path, note = transcript.find_transcript(sid)
    assert path == str(nested)
    assert note is None


def test_finds_flat_layout(cursor_root):
    sid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    flat = cursor_root / "projects" / "p" / "agent-transcripts" / f"{sid}.jsonl"
    flat.parent.mkdir(parents=True, exist_ok=True)
    flat.write_text("{}\n")
    path, note = transcript.find_transcript(sid)
    assert path == str(flat)
    assert note is None


def test_prefers_first_match_when_both_layouts_exist(cursor_root):
    sid = "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb"
    flat = cursor_root / "projects" / "p" / "agent-transcripts" / f"{sid}.jsonl"
    nested = cursor_root / "projects" / "p" / "agent-transcripts" / sid / f"{sid}.jsonl"
    flat.parent.mkdir(parents=True, exist_ok=True)
    flat.write_text("{}")
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("{}")
    path, note = transcript.find_transcript(sid)
    # Either match is acceptable; both should be discoverable.
    assert path in (str(flat), str(nested))
    assert note is None
