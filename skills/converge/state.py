"""Persistent state for the converge skill (single state.json file)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

STATE_PATH = Path.home() / ".claude" / "skills" / "converge" / "state.json"


class NoActiveSession(Exception):
    """Raised when an operation requires an active session but none exists."""


class StateCorrupt(Exception):
    """Raised when state.json exists but cannot be parsed into a State."""


@dataclass
class State:
    session_id: str
    round_count: int
    started_at: str
    last_status: str


def load() -> State | None:
    """Return the current state, None if no session exists, or raise StateCorrupt."""
    if not STATE_PATH.exists():
        return None
    try:
        data = json.loads(STATE_PATH.read_text())
        s = State(**data)
    except (json.JSONDecodeError, TypeError) as e:
        raise StateCorrupt(str(e)) from e
    if not (
        isinstance(s.session_id, str)
        and isinstance(s.round_count, int)
        and not isinstance(s.round_count, bool)
        and isinstance(s.started_at, str)
        and isinstance(s.last_status, str)
    ):
        raise StateCorrupt(
            f"field type mismatch: {data!r} does not match State schema"
        )
    return s


def save(s: State) -> None:
    """Atomically write state to disk."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(s), indent=2))
    tmp.replace(STATE_PATH)


def clear() -> None:
    """Delete the state file. Idempotent."""
    STATE_PATH.unlink(missing_ok=True)


def increment_round(new_status: str) -> int:
    """Increment round_count, set last_status, persist. Returns new round_count."""
    current = load()
    if current is None:
        raise NoActiveSession()
    current.round_count += 1
    current.last_status = new_status
    save(current)
    return current.round_count
