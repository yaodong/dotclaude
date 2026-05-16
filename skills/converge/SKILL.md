---
name: converge
description: "Critique-loop with Cursor's agent CLI as a read-only second-agent reviewer across spec → plan → code phases. Use when the user asks for Cursor's review on an artifact, asks about the current converge session, or wants to end the session."
---

# converge

Critique-loop with Cursor's `agent` CLI as a read-only second-agent reviewer. Use across spec → plan → code phases of a task. One Cursor chat persists across all phases; Cursor remembers the spec when reviewing the plan.

## When to use

- The user explicitly asks "have Cursor review this", "get a second opinion from Cursor", or similar.
- An artifact (spec, plan, code file) is ready for cross-agent critique and a converge session is active.
- The user asks about session state ("what round are we on?", "is converge running?") — call `status`.
- The user signals they're done ("we're done with converge", "end the session", "reset the converge state") — call `end`.

Do **not** invoke `start` or `iterate` for chitchat, casual questions, or speculative reviews — they spawn a real Cursor agent process and consume round budget. `status` and `end` are cheap and safe to call any time.

## Tools

All four are MCP tools the user invokes through natural language — there are no slash commands.

- **`converge.start(topic)`** — start a fresh Cursor chat. If `topic` is unclear, ask the user once before starting; don't invent one.
- **`converge.iterate(message, files)`** — submit one critique round. `files` is a list of absolute paths Cursor should read. Returns `{status, reply, round}` for active-session statuses; the `error` (corrupt state) and `no_session` branches return `{status, reply}` only.
- **`converge.status()`** — report session state.
- **`converge.end()`** — close the session. Idempotent and safe; also the escape hatch when state is corrupt.

### Decision flow when the user asks for a review

1. Call `status`. If `no_session`, call `start(topic)`. If `state_corrupt`, call `end` to clear, then `start`.
2. Once a session is active, revise the artifact (or stage the file the user wants reviewed), then call `iterate(message, files)`.
3. Loop on `iterate` per "Reading the reply" below until `STATUS: APPROVED` or you hit a stop condition in "Critical behavior rules."

Do not skip `status` and call `iterate` directly — that returns `no_session` and wastes a round of the user's attention.

### How to handle each tool's response

**`start` returns** `{ok, ...}`:

- `ok: true` → tell the user the session_id and confirm Cursor acknowledged the contract.
- `ok: false, reason: "session_active"` → a session is already active; show its session_id and ask whether to end it first.
- `ok: false, reason: "seed_not_acknowledged"` → show Cursor's `reply` verbatim. Do not auto-retry — the user decides whether to retry or investigate.
- `ok: false, reason: "state_corrupt"` → state file is corrupt; show `error`; suggest ending the session to clear it before retrying.
- `ok: false, reason: "agent_cli_error"` → show `error`; the `agent` CLI failed. Common causes: missing from PATH, network/auth, or Cursor workspace-trust not granted (`error` will say "Workspace Trust Required"). The trust prompt is interactive and can't be answered via MCP — tell the user to open a real terminal, `cd` to the directory, run `agent`, accept the prompt, and exit. Trust persists per-directory after that. Do not auto-retry.
- Any other `ok: false` → show the full response and ask how to proceed.

**`iterate` returns** `{status, reply, round}` for active-session statuses; the `error` (corrupt state) and `no_session` branches return `{status, reply}` only. See "Reading the reply" below.

**`status` returns** `{ok, ...}`:

- `ok: true` → report compactly: session_id, round_count (out of 30), started_at, last_status, transcript_path (or `transcript_note` if path is null).
- `ok: false, reason: "no_session"` → say "No active converge session" plainly.
- `ok: false, reason: "state_corrupt"` → state is corrupt; show `error`; suggest ending to clear it.
- Any other `ok: false` → show the full response.

**`end` returns** `{ok: true, ...}` (always). Distinguish three cases:

- `ended_session_id: <id>` present → confirm the session ended; show the id, and mention the Cursor chat is preserved in Cursor's storage and resumable via `agent --resume <id>`.
- `no_session: true` → say "No active converge session to end." Don't mention resume — there was no chat.
- `cleared_corrupt_state: true` → tell the user the state file was corrupt and has been cleared. The underlying Cursor chat (if any) may still exist in Cursor's storage but the server can't tell you the id; if they have it from earlier, they can `agent --resume <id>` manually.

## How to call iterate

`message` is free-form (no fixed template). It conveys:

- **What artifact** changed (which file).
- **What changed** — one line per addressed finding, referenced by Cursor's prior numbering when applicable ("addressed point 2 by …").
- **What didn't change and why** — push-backs and accepted limitations, with the reason inline.
- **What you want from this round** — re-review, an opinion on a tradeoff, etc.

Format follows the content. A single one-line fix gets a one-line message. A multi-finding revision gets a numbered list. Do not pad with empty sections.

`files` should be **absolute paths**. The MCP server passes them through; Cursor's file tools expect absolutes.

## Reading the reply

`iterate` returns `{status, reply, round}` for active-session statuses; the `error` (corrupt state) and `no_session` branches return `{status, reply}` only. Behavior by status:

- **`approved`** → move on. The artifact is good as-is.
- **`changes_requested`** → revise the file, then call `iterate` again with a message describing what changed.
- **`needs_info`** → answer Cursor's questions in the next `iterate` call without revising the artifact (unless an answer reveals the artifact actually needs a change). If you can't answer the question — it requires the user's judgment, missing domain knowledge, or contradicts your own assumptions — surface to user. Do not invent answers to keep the loop going.
- **`ambiguous`** → call `iterate` once more asking Cursor to add the STATUS line per the contract: "Please add the STATUS: line to your last reply per the contract." If still ambiguous, surface to user.
- **`limit_reached`** or **`no_session`** → surface to user.
- **`error`** → surface to user with the reply text (it contains stderr).

## Critical behavior rules

1. **Break the loop and surface to user any time:**
   - You don't have the information needed to address Cursor's feedback.
   - Cursor's feedback contradicts the user's stated intent.
   - You'd need to invent a requirement, value, or design choice to keep going.
   - The feedback is a tradeoff that needs the user's judgment.

2. **Never make assumptions to satisfy Cursor.** Stop is better than guess.

3. **Convergence is not capitulation. For each finding:**
   - **Verify first.** Cursor's claim might be wrong — incorrect facts, stale documentation, misreading the artifact. Check it against the actual file, the user's stated intent, and any available evidence (e.g., `agent --list-models` output, file contents, recent git history) before choosing a response. Do not act on findings without verifying them.
   - **Revise** when verified feedback identifies a real gap or error.
   - **Accept as known limitation** when the concern is real but the tradeoff is intentional. Document the acceptance in the artifact itself, then in the next iterate call note: "noted; intentional, see section X — keeping as-is."
   - **Push back** when verification shows the finding is wrong on the merits. State the reason concisely with evidence (e.g., "I disagree with point 3 — `agent --list-models` shows the model is available; the docs Cursor cites may be incomplete. Keeping as-is. Please confirm or counter."). Cursor may concede, escalate, or stand firm.
   - **Surface to user** when the disagreement is a judgment call you can't resolve, or when verification reveals the user needs to decide. Don't grind in the loop.

4. The goal is convergence on a *correct* artifact, not on Cursor's preferences. `STATUS: APPROVED` is the loop-exit signal, not a quality bar.

5. **Always re-submit after addressing feedback.** Even when you believe you've fully resolved every comment, call `iterate` again with a summary of what changed. Do not assume the artifact is done. Cursor frequently catches issues introduced by the fix itself, things missed in the prior pass, and misunderstandings of the original feedback. Only treat the artifact as converged when Cursor returns `STATUS: APPROVED` *after seeing your latest revision*.

## File conventions

- **Default:** the artifact already exists. Update the file, then `iterate` with `message="I've updated <basename>. <one-line summary>"` and `files=[absolute path]`.
- **Optional fallback:** if you need Cursor's input on something with no existing home AND it's substantial:
  - Prefer to ask the user where to put it.
  - Only create a new file unprompted when waiting for user input would interrupt flow.
  - New files go inside the project (any path you judge appropriate).
- **Short clarifying questions with no natural file:** ask the user, not Cursor.

## Antipattern: parallel converge sessions

If two Claude Code instances are running simultaneously, both will share the same converge state file and race on round_count writes. Avoid running converge from multiple Claude Code sessions at once. There is no cross-instance coordination in v1.
