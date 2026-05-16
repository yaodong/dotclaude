"""Builds the seed prompt sent to Cursor at /converge-start."""
from __future__ import annotations

_TEMPLATE = """\
We're going to collaborate on a task: {topic}.

I will send you spec, plan, and code artifacts to review across the next several rounds. You are reviewing in read-only mode — do not write or edit files. Read the file paths I provide using your own tools each round (the file content may have changed since you last read it).

## How to review

- Read the referenced file(s) fresh each round.
- Return findings as a list. For each finding:
  - **Severity:** high / medium / low.
  - **Location:** file path and line numbers (or section heading if line numbers don't apply).
  - **Issue:** describe the problem; do not prescribe the fix unless asked.
- Group findings by file when multiple files are reviewed.
- If you have no findings, say so explicitly.

## Status trailer (REQUIRED)

End every reply with exactly one of these lines, on its own line, as the last non-empty line of your message:

- STATUS: APPROVED            (no further changes required; the artifact is good as-is)
- STATUS: CHANGES_REQUESTED   (you have concrete findings that require revising the artifact)
- STATUS: NEEDS_INFO          (the artifact may be fine, but you have open questions that need answers before you can approve)

Use NEEDS_INFO when you need clarification, missing context, or answers from the author — questions that don't necessarily require changing the artifact. Use CHANGES_REQUESTED when you have specific revision requests for the artifact itself. If you have both, use CHANGES_REQUESTED.

This line is parsed mechanically; it controls our review loop. Do not omit it. Do not vary the wording.

## Acknowledge

Reply with "Acknowledged" and STATUS: APPROVED if you understand the contract.
"""


def build_seed_prompt(topic: str) -> str:
    """Return the seed message. `topic` is empty-string-safe (falls back to 'TBD')."""
    return _TEMPLATE.format(topic=topic.strip() or "TBD")
