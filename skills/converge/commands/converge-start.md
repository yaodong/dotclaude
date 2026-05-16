Start a new converge critique session.

Topic: $ARGUMENTS

Call `converge.start` with the topic above (or empty string if no topic was provided).

Handle the response by `ok` and `reason`:

- `ok: true` → report the session_id and confirm the contract was acknowledged.
- `ok: false, reason: "session_active"` → tell me a session is already active (show the existing session_id) and ask whether to `/converge-end` first.
- `ok: false, reason: "seed_not_acknowledged"` → show me Cursor's reply verbatim so I can decide whether to retry or investigate. Do NOT auto-retry.
- `ok: false, reason: "state_corrupt"` → tell me the state file is corrupt; show the `error` field; suggest running `/converge-end` to clear it before retrying.
- `ok: false, reason: "agent_cli_error"` → show me the `error` field; the `agent` CLI failed (likely missing from PATH, network issue, or auth problem). Do NOT auto-retry.
- Any other `ok: false` → show the full response and ask me how to proceed.
