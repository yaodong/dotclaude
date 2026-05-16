---
name: bitbucket-pull-requests
description: Use when creating, viewing, updating, commenting on, or merging a pull request on Bitbucket Cloud (bitbucket.org remotes). Use the bundled bitbucket_api.py tool — never write ad-hoc curl scripts to hit the Bitbucket API.
---

# Bitbucket Cloud Pull Requests

## Overview

Bitbucket Cloud has no official CLI (`acli` covers Jira and Rovo Dev only, not Bitbucket). This skill provides a stdlib-only Python tool that wraps the Bitbucket Cloud REST API.

**Iron rule: do not write ad-hoc curl/python scripts to call the Bitbucket API.** Use `bitbucket_api.py`. If a needed operation is missing, extend the tool — don't bypass it.

## When to use

- "Create a PR for this branch"
- "Update the PR title or description"
- "Add a comment to PR #123"
- "Merge PR #123"
- "What's in PR #123?"
- "List my open PRs on this repo"
- Any Bitbucket Cloud PR operation from CLI

**Don't use for:** GitHub (use `gh`), Bitbucket Data Center / Server (different API), Bitbucket Pipelines management.

## Setup (one-time)

1. Create an Atlassian API token at https://id.atlassian.com/manage-profile/security/api-tokens
   - Scoped tokens: include `Pull requests: write` on the target repo
2. Export credentials (e.g. in `~/.zshrc`):
   ```sh
   export BITBUCKET_EMAIL="you@leantaas.com"
   export BITBUCKET_API_TOKEN="ATATT3x..."
   ```
3. Auth model: HTTP Basic with `email:token`. Workspace + repo slug are auto-parsed from `git remote get-url origin`.

## Quick reference

Run from inside a git checkout of the target repo. Set `BB=python3 ~/.claude/skills/bitbucket-pull-requests/bitbucket_api.py` to keep the table readable.

| Task | Command |
|------|---------|
| Create PR (current branch → main) from a file | `$BB create -t "TITLE" -F body.md` |
| Create PR with explicit branches | `$BB create -t "TITLE" -s feature/x -D master -F body.md` |
| Create PR composing in `$EDITOR` | `$BB create -t "TITLE" --edit` |
| Update description from a file | `$BB update-description 123 -F new_body.md` |
| Update description in `$EDITOR` (pre-filled) | `$BB update-description 123 --edit` |
| Update title | `$BB update-title 123 -t "New title"` |
| Add a comment | `$BB comment 123 -F note.md` (or `--edit`, or `-d "..."`) |
| Merge a PR | `$BB merge 123 --strategy squash --close-source-branch` |
| View a PR | `$BB view 123` |
| List open PRs (default limit 25) | `$BB list` |
| List open PRs for current branch | `$BB list --branch $(git branch --show-current)` |
| List with custom limit | `$BB list --state MERGED --limit 100` |

`-F -` reads from stdin if you really want to pipe (`some_cmd | $BB ... -F -`); for plain files, prefer `-F body.md`.

## Conventions

- **Body input options (`create`, `update-description`, `comment`):** `-d "string"` for one-liners, `-F file.md` for prepared content, `--edit` to compose in `$EDITOR`. They are mutually exclusive.
- **`--edit` pre-populates** with current content for `update-description` and `update-title`. For `create`, the editor opens with a comment header listing source/dest branches and the commits being included; lines starting with `#` at the top are stripped on save.
- **`update-description` and `update-title` replace** the existing value entirely. To append to a description, use `--edit`.
- **Reviewers:** `--reviewer` accepts UUID (preferred, wrapped in `{braces}`) or username. UUID is more reliable — Bitbucket has been deprecating username-based lookups.
- **Output:** mutating commands print `{"id": N, "url": "..."}` on success — surface the URL to the user.
- **`list` pagination:** default `--limit 25`. If more results exist, a `(+N more — re-run with --limit N)` hint is printed to stderr.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Using `gh` on a Bitbucket repo | `gh` is GitHub-only. Use this tool. |
| Writing a one-off `curl` to hit the API | Forbidden by this skill. Add a subcommand to `bitbucket_api.py` if needed. |
| Passing description inline with newlines | Use `-F file.md` or `--edit`. |
| Forgetting `--workspace`/`--repo` outside a git checkout | Either `cd` into the repo or pass both flags explicitly. |
| Token with wrong scope → 403 | Token needs `Pull requests: write` on that specific repo. The tool's 403 message says this. |

## Extending the tool

Need a new operation (decline PR, approve/unapprove, request changes, manage reviewers post-create, fetch diff)? Add a subcommand to `bitbucket_api.py` and document it in the table above. The Bitbucket REST API base is `https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/...`. Auth is already wired up; reuse `_request(method, path, body)`. For body input, reuse `_resolve_body(args, ...)` so the new command supports `-d`/`-F`/`--edit` consistently.
