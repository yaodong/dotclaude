Report the current converge session status.

Call `converge.status`. Handle the response by `ok` and `reason`:

- `ok: true` → report as a compact list:
  - session_id
  - round_count (out of 30)
  - started_at
  - last_status
  - transcript_path (or `transcript_note` if path is null)
- `ok: false, reason: "no_session"` → say "No active converge session." plainly.
- `ok: false, reason: "state_corrupt"` → tell me the state file is corrupt; show the `error` field; suggest running `/converge-end` to clear it.
- Any other `ok: false` → show the full response.
