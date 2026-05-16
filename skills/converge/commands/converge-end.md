End the current converge session.

Call `converge.end`. The response always has `ok: true` (end is idempotent and safe). Distinguish three cases:

- `ended_session_id: <id>` present → confirm the session was ended; show the id.
- `no_session: true` → say "No active converge session to end."
- `cleared_corrupt_state: true` → tell me the state file was corrupt and has been cleared; the underlying Cursor chat (if any) may still exist and can be resumed manually with `agent --resume <id>` if I know the id.

In all three cases, mention that the Cursor chat itself is preserved in Cursor's storage and can be resumed via `agent --resume <id>` if needed.
