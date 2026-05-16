"""Parse the STATUS: trailer from a Cursor agent reply."""
from __future__ import annotations

import re

_PATTERN = re.compile(r"^\s*status\s*:\s*(approved|changes_requested|needs_info)\s*$", re.IGNORECASE)


def parse_status(reply: str) -> str:
    """Return one of: approved, changes_requested, needs_info, ambiguous.

    Looks at the last non-empty line of `reply`. If it matches the trailer
    pattern (case-insensitive, whitespace-tolerant), returns the corresponding
    lowercase status. Otherwise returns "ambiguous".
    """
    lines = [ln for ln in reply.splitlines() if ln.strip()]
    if not lines:
        return "ambiguous"
    m = _PATTERN.match(lines[-1])
    return m.group(1).lower() if m else "ambiguous"
