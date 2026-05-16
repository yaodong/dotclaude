"""MCP server exposing the converge tools."""
from __future__ import annotations

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from converge import agent_cli, parser, prompt, seed, state, transcript

MAX_ROUNDS = 30

mcp = FastMCP("converge")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def start_impl(topic: str) -> dict:
    """Start a new converge session. See spec converge.start()."""
    try:
        current = state.load()
    except state.StateCorrupt as e:
        return {"ok": False, "reason": "state_corrupt", "error": str(e)}
    if current is not None:
        return {
            "ok": False,
            "reason": "session_active",
            "session_id": current.session_id,
        }

    try:
        session_id = agent_cli.create_chat()
    except agent_cli.AgentCliError as e:
        return {"ok": False, "reason": "agent_cli_error", "error": str(e)}

    seed_prompt = seed.build_seed_prompt(topic)
    try:
        reply = agent_cli.run_prompt(session_id, seed_prompt)
    except agent_cli.AgentCliError as e:
        return {
            "ok": False,
            "reason": "agent_cli_error",
            "session_id": session_id,
            "error": str(e),
        }

    status = parser.parse_status(reply)
    if status != "approved":
        return {
            "ok": False,
            "reason": "seed_not_acknowledged",
            "session_id": session_id,
            "reply": reply,
        }

    state.save(state.State(
        session_id=session_id,
        round_count=0,
        started_at=_utc_now_iso(),
        last_status="approved",
    ))
    return {"ok": True, "session_id": session_id, "reply": reply}


@mcp.tool()
def start(topic: str = "") -> dict:
    """Start a fresh Cursor critique chat for a new task.

    Use when the user asks for a Cursor review and no session is active.
    Creates a Cursor chat, seeds the review contract, and confirms Cursor
    acknowledges. Returns ok=False if a session is already active or if
    Cursor doesn't acknowledge the seed.
    """
    return start_impl(topic)


def iterate_impl(message: str, files: list[str]) -> dict:
    """Send one round to Cursor. See spec converge.iterate()."""
    try:
        current = state.load()
    except state.StateCorrupt as e:
        return {
            "status": "error",
            "reply": f"state file corrupted, call converge.end then converge.start: {e}",
        }
    if current is None:
        return {
            "status": "no_session",
            "reply": "no active converge session; call converge.start first",
        }
    if current.round_count >= MAX_ROUNDS:
        return {
            "status": "limit_reached",
            "reply": f"{MAX_ROUNDS}-round cap reached; call converge.end then converge.start to continue",
            "round": current.round_count,
        }

    formatted = prompt.format_iterate_prompt(message, files)
    try:
        reply = agent_cli.run_prompt(current.session_id, formatted)
    except agent_cli.AgentCliError as e:
        new_count = state.increment_round("error")
        return {
            "status": "error",
            "reply": str(e),
            "round": new_count,
        }

    status = parser.parse_status(reply)
    new_count = state.increment_round(status)
    return {"status": status, "reply": reply, "round": new_count}


@mcp.tool()
def iterate(message: str, files: list[str] = []) -> dict:
    """Send one critique round to the active Cursor chat.

    `message` is a free-form note (what you changed, what you want reviewed).
    `files` is a list of absolute paths Cursor should read this round.
    Returns {status, reply, round}. status is one of: approved,
    changes_requested, needs_info, ambiguous, error, no_session, limit_reached.
    """
    return iterate_impl(message, files)


def status_impl() -> dict:
    try:
        current = state.load()
    except state.StateCorrupt as e:
        return {"ok": False, "reason": "state_corrupt", "error": str(e)}
    if current is None:
        return {"ok": False, "reason": "no_session"}
    transcript_path, transcript_note = transcript.find_transcript(current.session_id)
    return {
        "ok": True,
        "session_id": current.session_id,
        "round_count": current.round_count,
        "started_at": current.started_at,
        "last_status": current.last_status,
        "transcript_path": transcript_path,
        "transcript_note": transcript_note,
    }


@mcp.tool()
def status() -> dict:
    """Report the current converge session state, or no_session if none."""
    return status_impl()


def end_impl() -> dict:
    # `end` must work even when state is corrupt — that's the whole point of having
    # an escape hatch. Bypass `load()` and clear unconditionally.
    try:
        current = state.load()
    except state.StateCorrupt:
        state.clear()
        return {"ok": True, "cleared_corrupt_state": True}
    state.clear()
    if current is None:
        return {"ok": True, "no_session": True}
    return {"ok": True, "ended_session_id": current.session_id}


@mcp.tool()
def end() -> dict:
    """End the current converge session. Idempotent."""
    return end_impl()


if __name__ == "__main__":
    # Fail fast if `agent` isn't on PATH — surfaces as a clear MCP startup error
    # rather than a silent failure on the first tool call.
    agent_cli.check_agent_available()
    mcp.run()
