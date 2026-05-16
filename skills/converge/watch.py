"""Watch (tail) a Cursor agent transcript with markdown rendering.

Usage:
    python3 -m converge.watch              # interactive picker
    python3 -m converge.watch <session-id> # tail a specific session

Run from another terminal pane while you work in Claude Code. Discovers
sessions under ~/.cursor/projects/*/agent-transcripts/, sorted by recency.
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from converge import state, transcript

MAX_SESSIONS = 10
TITLE_WIDTH = 40
USER_QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)


@dataclass
class SessionEntry:
    session_id: str
    transcript_path: Path
    mtime: float
    turn_count: int
    title: str
    is_active: bool


def _read_first_user_message(jsonl_path: Path) -> str:
    """Return the first user-message text from a transcript, or empty string."""
    try:
        with jsonl_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("role") != "user":
                    continue
                content = obj.get("message", {}).get("content", [])
                if not content:
                    continue
                text = content[0].get("text", "")
                m = USER_QUERY_RE.search(text)
                if m:
                    return m.group(1)
                return text
    except OSError:
        pass
    return ""


def _count_turns(jsonl_path: Path) -> int:
    try:
        with jsonl_path.open() as f:
            return sum(1 for ln in f if ln.strip())
    except OSError:
        return 0


def _truncate(s: str, width: int) -> str:
    s = " ".join(s.split())  # collapse whitespace
    if len(s) <= width:
        return s
    return s[: width - 3] + "..."


def _format_timestamp(ts: float) -> str:
    now = datetime.now()
    dt = datetime.fromtimestamp(ts)
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    if (now - dt).days < 7:
        return dt.strftime("%a %H:%M")
    return dt.strftime("%Y-%m-%d")


def discover_sessions(active_session_id: str | None = None) -> list[SessionEntry]:
    """Find recent transcripts under ~/.cursor/projects/."""
    cursor_root = Path.home() / ".cursor" / "projects"
    if not cursor_root.exists():
        return []

    candidates: list[tuple[Path, str]] = []  # (path, session_id)

    # Nested layout: */agent-transcripts/<sid>/<sid>.jsonl
    for path in cursor_root.glob("*/agent-transcripts/*/*.jsonl"):
        if path.parent.name == path.stem:
            candidates.append((path, path.stem))

    # Flat layout: */agent-transcripts/<sid>.jsonl
    for path in cursor_root.glob("*/agent-transcripts/*.jsonl"):
        # Skip if its parent is itself an sid-named dir (already handled above).
        if path.parent.name == path.stem:
            continue
        candidates.append((path, path.stem))

    entries: list[SessionEntry] = []
    seen_ids: set[str] = set()
    for path, sid in candidates:
        if sid in seen_ids:
            continue
        seen_ids.add(sid)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        entries.append(SessionEntry(
            session_id=sid,
            transcript_path=path,
            mtime=mtime,
            turn_count=_count_turns(path),
            title=_read_first_user_message(path),
            is_active=(sid == active_session_id),
        ))

    entries.sort(key=lambda e: e.mtime, reverse=True)
    return entries[:MAX_SESSIONS]


def load_active_session_id() -> str | None:
    try:
        s = state.load()
    except state.StateCorrupt:
        return None
    return s.session_id if s else None


def pick_session(entries: list[SessionEntry]) -> SessionEntry | None:
    """Print picker, read user choice, return chosen entry."""
    if not entries:
        print("No transcripts found under ~/.cursor/projects/.")
        return None

    print("Recent converge sessions:")
    short_id_w = 8
    for i, e in enumerate(entries, 1):
        short_id = e.session_id[:short_id_w]
        ts = _format_timestamp(e.mtime)
        title = _truncate(e.title or "(no title)", TITLE_WIDTH)
        active = " [active]" if e.is_active else ""
        print(f"  {i:2}. {short_id}  {ts:<10}  {e.turn_count:>3}t  {title}{active}")
    print()

    try:
        raw = input("Pick [1]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not raw:
        return entries[0]
    try:
        idx = int(raw)
    except ValueError:
        print(f"Not a number: {raw!r}", file=sys.stderr)
        return None
    if not 1 <= idx <= len(entries):
        print(f"Out of range: {idx}", file=sys.stderr)
        return None
    return entries[idx - 1]


def _render_turn(role: str, text: str, turn: int) -> None:
    """Render one transcript turn using rich panels with markdown."""
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    # Strip our own <user_query> wrapper for cleaner display.
    m = USER_QUERY_RE.search(text)
    body = m.group(1) if m else text

    # Strip the [REDACTED] trailer Cursor adds.
    body = re.sub(r"\n+\[REDACTED\].*$", "", body, flags=re.DOTALL).strip()

    color = {"user": "cyan", "assistant": "green"}.get(role, "white")
    console = Console()
    console.print(Panel(
        Markdown(body) if body else "(empty)",
        title=f"{role} (turn {turn})",
        title_align="left",
        border_style=color,
    ))
    console.print()


def tail(path: Path) -> None:
    """Print all existing turns, then follow the file for new turns."""
    turn = 0
    buf = ""

    def flush_complete_objects() -> None:
        """Parse complete JSON objects from `buf`, render each, advance buf."""
        nonlocal buf, turn
        decoder = json.JSONDecoder()
        while True:
            stripped = buf.lstrip()
            if not stripped:
                buf = stripped
                return
            try:
                obj, end = decoder.raw_decode(stripped)
            except json.JSONDecodeError:
                buf = stripped
                return
            buf = stripped[end:]
            turn += 1
            role = obj.get("role", "?")
            content = obj.get("message", {}).get("content", [])
            text = content[0].get("text", "") if content else ""
            _render_turn(role, text, turn)

    # Open the file and follow it; tolerate it not yet existing (e.g.,
    # session created but no turn yet).
    print(f"watching: {path}", file=sys.stderr)
    while not path.exists():
        time.sleep(0.5)

    with path.open() as f:
        # Initial pass: read everything currently in the file.
        chunk = f.read()
        if chunk:
            buf += chunk
            flush_complete_objects()

        # Follow loop.
        while True:
            chunk = f.read()
            if chunk:
                buf += chunk
                flush_complete_objects()
                continue
            time.sleep(0.5)


def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: converge-watch [session-id]", file=sys.stderr)
        return 2

    active_sid = load_active_session_id()

    if len(sys.argv) == 2:
        sid = sys.argv[1]
        path, note = transcript.find_transcript(sid)
        if path is None:
            print(f"No transcript found for {sid}: {note}", file=sys.stderr)
            return 1
        chosen_path = Path(path)
    else:
        entries = discover_sessions(active_sid)
        choice = pick_session(entries)
        if choice is None:
            return 1
        chosen_path = choice.transcript_path

    try:
        tail(chosen_path)
    except KeyboardInterrupt:
        print()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
