"""Format the iterate() prompt sent to Cursor."""
from __future__ import annotations

from pathlib import PurePath


def format_iterate_prompt(message: str, files: list[str]) -> str:
    """Combine message with a Contexts: block listing each file by basename."""
    if not files:
        return message
    lines = [message, "", "Contexts:"]
    for f in files:
        lines.append(f" - {PurePath(f).name}: {f}")
    return "\n".join(lines)
