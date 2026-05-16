"""Tests for the pure helpers in watch.py.

Skips the interactive picker (input prompts), the rich-renderer panels, and the
infinite tail loop — those are tested by hand. Covers what could silently break:
session discovery, title extraction, truncation, timestamp formatting, and the
JSON-boundary parser.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from converge import watch


# ---------- _truncate ----------

def test_truncate_short_string_unchanged():
    assert watch._truncate("hello", 40) == "hello"


def test_truncate_long_string_appends_ellipsis():
    out = watch._truncate("a" * 50, 40)
    assert len(out) == 40
    assert out.endswith("...")
    assert out.startswith("a" * 37)


def test_truncate_collapses_whitespace():
    assert watch._truncate("hello\n\n  world", 40) == "hello world"


def test_truncate_collapses_then_truncates():
    out = watch._truncate("hello\n\n  " + "x" * 100, 20)
    assert len(out) == 20
    assert out.endswith("...")
    assert "\n" not in out


# ---------- _format_timestamp ----------

def test_format_timestamp_today_shows_hh_mm():
    ts = datetime.now().replace(hour=14, minute=26, second=0, microsecond=0).timestamp()
    out = watch._format_timestamp(ts)
    assert out == "14:26"


def test_format_timestamp_within_week_shows_weekday():
    ts = (datetime.now() - timedelta(days=3)).timestamp()
    out = watch._format_timestamp(ts)
    # Format is like "Tue 14:26" — weekday + time, separated by space.
    parts = out.split()
    assert len(parts) == 2
    assert parts[0] in {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}


def test_format_timestamp_old_shows_date():
    ts = (datetime.now() - timedelta(days=30)).timestamp()
    out = watch._format_timestamp(ts)
    # Format like "2026-04-15".
    assert len(out) == 10
    assert out[4] == "-" and out[7] == "-"


# ---------- _read_first_user_message ----------

def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


def test_read_first_user_message_extracts_user_query_tag(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>\nReview the spec\n</user_query>"}]}},
        {"role": "assistant", "message": {"content": [{"type": "text", "text": "ok"}]}},
    ])
    assert watch._read_first_user_message(p) == "Review the spec"


def test_read_first_user_message_falls_back_to_raw_text(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        {"role": "user", "message": {"content": [{"type": "text", "text": "no tags here"}]}},
    ])
    assert watch._read_first_user_message(p) == "no tags here"


def test_read_first_user_message_skips_assistant_turns(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        {"role": "assistant", "message": {"content": [{"type": "text", "text": "I am the assistant"}]}},
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>actual user msg</user_query>"}]}},
    ])
    assert watch._read_first_user_message(p) == "actual user msg"


def test_read_first_user_message_handles_blank_lines(tmp_path):
    p = tmp_path / "t.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\n\n"
        + json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>hi</user_query>"}]}})
        + "\n\n"
    )
    assert watch._read_first_user_message(p) == "hi"


def test_read_first_user_message_returns_empty_when_missing(tmp_path):
    assert watch._read_first_user_message(tmp_path / "nope.jsonl") == ""


def test_read_first_user_message_returns_empty_when_no_user_turn(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        {"role": "assistant", "message": {"content": [{"type": "text", "text": "lone reply"}]}},
    ])
    assert watch._read_first_user_message(p) == ""


def test_read_first_user_message_tolerates_corrupt_line(tmp_path):
    """If a line is malformed JSON, skip it and continue."""
    p = tmp_path / "t.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "{not json\n"
        + json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>real</user_query>"}]}})
        + "\n"
    )
    assert watch._read_first_user_message(p) == "real"


# ---------- _count_turns ----------

def test_count_turns(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [{"role": "user"}, {"role": "assistant"}, {"role": "user"}])
    assert watch._count_turns(p) == 3


def test_count_turns_ignores_blank_lines(tmp_path):
    p = tmp_path / "t.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}\n\n{}\n  \n{}\n")
    assert watch._count_turns(p) == 3


def test_count_turns_zero_when_missing(tmp_path):
    assert watch._count_turns(tmp_path / "nope.jsonl") == 0


# ---------- discover_sessions ----------


class _PathFactory:
    """Make Path() work normally, but Path.home() return a fake dir."""

    def __init__(self, fake_home: Path):
        self._fake_home = fake_home
        self._real_path = Path

    def __call__(self, *args, **kwargs):
        return self._real_path(*args, **kwargs)

    def home(self) -> Path:
        return self._fake_home

    def __getattr__(self, name):
        return getattr(self._real_path, name)


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Patch watch.Path so Path.home() inside watch.py returns tmp_path."""
    monkeypatch.setattr(watch, "Path", _PathFactory(tmp_path))
    return tmp_path


def _make_transcript(home: Path, project: str, sid: str, *, nested: bool, lines: list[dict]) -> Path:
    """Create a transcript file at home/.cursor/projects/<project>/agent-transcripts/..."""
    base = home / ".cursor" / "projects" / project / "agent-transcripts"
    if nested:
        path = base / sid / f"{sid}.jsonl"
    else:
        path = base / f"{sid}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def test_discover_sessions_empty_when_no_cursor_dir(fake_home):
    # fake_home exists but contains no .cursor/ tree.
    assert watch.discover_sessions() == []


def test_discover_sessions_finds_nested_layout(fake_home):
    sid = "11111111-2222-3333-4444-555555555555"
    _make_transcript(fake_home, "proj1", sid, nested=True, lines=[
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>one</user_query>"}]}},
    ])
    entries = watch.discover_sessions()
    assert len(entries) == 1
    assert entries[0].session_id == sid
    assert entries[0].title == "one"
    assert entries[0].turn_count == 1
    assert entries[0].is_active is False


def test_discover_sessions_finds_flat_layout(fake_home):
    sid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    _make_transcript(fake_home, "proj", sid, nested=False, lines=[
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>flat</user_query>"}]}},
    ])
    entries = watch.discover_sessions()
    assert len(entries) == 1
    assert entries[0].session_id == sid
    assert entries[0].title == "flat"


def test_discover_sessions_marks_active(fake_home):
    sid = "active-id-1234"
    _make_transcript(fake_home, "proj", sid, nested=True, lines=[
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>active!</user_query>"}]}},
    ])
    entries = watch.discover_sessions(active_session_id=sid)
    assert len(entries) == 1
    assert entries[0].is_active is True


def test_discover_sessions_sorted_by_mtime_desc(fake_home):
    import os
    older = _make_transcript(fake_home, "p", "older-id", nested=True, lines=[
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>older</user_query>"}]}},
    ])
    newer = _make_transcript(fake_home, "p", "newer-id", nested=True, lines=[
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>newer</user_query>"}]}},
    ])
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))
    entries = watch.discover_sessions()
    assert [e.session_id for e in entries] == ["newer-id", "older-id"]


def test_discover_sessions_dedupes_when_both_layouts_exist(fake_home):
    """If somehow both nested and flat exist for the same SID, only one entry."""
    sid = "dup-id-1234"
    _make_transcript(fake_home, "p", sid, nested=True, lines=[
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>nested wins</user_query>"}]}},
    ])
    _make_transcript(fake_home, "p", sid, nested=False, lines=[
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>flat loses</user_query>"}]}},
    ])
    entries = watch.discover_sessions()
    assert len(entries) == 1
    assert entries[0].session_id == sid


def test_discover_sessions_caps_at_max(fake_home):
    """At most MAX_SESSIONS entries returned even when more exist."""
    for i in range(watch.MAX_SESSIONS + 5):
        _make_transcript(fake_home, "p", f"sid-{i:02d}", nested=True, lines=[
            {"role": "user", "message": {"content": [{"type": "text", "text": f"<user_query>msg {i}</user_query>"}]}},
        ])
    entries = watch.discover_sessions()
    assert len(entries) == watch.MAX_SESSIONS
