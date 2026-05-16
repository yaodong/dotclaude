"""Best-effort discovery of the Cursor agent JSONL transcript for a session."""
from __future__ import annotations

from pathlib import Path

CURSOR_ROOT = Path.home() / ".cursor"


def find_transcript(session_id: str) -> tuple[str | None, str | None]:
    """Return (path, note). path is the absolute path string or None.
    note is None on success, else an explanation when the path can't be found.
    """
    transcripts_root = CURSOR_ROOT / "projects"
    if not transcripts_root.exists():
        return None, "transcript file not found at known locations; layout may have changed"

    nested = list(transcripts_root.glob(f"*/agent-transcripts/{session_id}/{session_id}.jsonl"))
    if nested:
        return str(nested[0]), None

    flat = list(transcripts_root.glob(f"*/agent-transcripts/{session_id}.jsonl"))
    if flat:
        return str(flat[0]), None

    return None, "transcript file not found at known locations; layout may have changed"
