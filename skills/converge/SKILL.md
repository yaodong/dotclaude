---
name: converge
description: "Critique-loop with Cursor's agent CLI as a read-only second-agent reviewer across spec → plan → code phases. Use when the user invokes /converge-start, /converge-status, or /converge-end, or asks for Cursor's review on an artifact."
---

# converge

Critique-loop with Cursor's `agent` CLI as a read-only second-agent reviewer. Use across spec → plan → code phases of a task. One Cursor chat persists across all phases; Cursor remembers the spec when reviewing the plan.

## When to use

- The user has invoked `/converge-start`, `/converge-status`, or `/converge-end`.
- The user explicitly asks "have Cursor review this" or similar.
- An artifact (spec, plan, code file) is ready for cross-agent critique and a converge session is active.

Do **not** invoke converge for chitchat, casual questions, or anything that isn't an artifact-level review request. The tool spawns a real Cursor agent process and consumes round budget.

## Tools

- **`converge.start(topic)`** — start a fresh Cursor chat. Use only when responding to `/converge-start`.
- **`converge.iterate(message, files)`** — submit one critique round. `files` is a list of absolute paths Cursor should read. Returns `{status, reply, round}`.
- **`converge.status()`** — report session state. Use for `/converge-status`.
- **`converge.end()`** — close the session. Use for `/converge-end`.

## How to call iterate

`message` is free-form (no fixed template). It conveys:

- **What artifact** changed (which file).
- **What changed** — one line per addressed finding, referenced by Cursor's prior numbering when applicable ("addressed point 2 by …").
- **What didn't change and why** — push-backs and accepted limitations, with the reason inline.
- **What you want from this round** — re-review, an opinion on a tradeoff, etc.

Format follows the content. A single one-line fix gets a one-line message. A multi-finding revision gets a numbered list. Do not pad with empty sections.

`files` should be **absolute paths**. The MCP server passes them through; Cursor's file tools expect absolutes.

## Reading the reply

`iterate` returns `{status, reply, round}`. Behavior by status:

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
