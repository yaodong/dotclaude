# agentic

Modular skills and agent configurations for AI agents.

## Skills

| Skill | Description | Source |
| --- | --- | --- |
| [`bitbucket-pull-requests`](skills/bitbucket-pull-requests) | Create and update Bitbucket Cloud pull requests via a stdlib-only Python wrapper around the REST API | me |
| [`conventional-commit`](skills/conventional-commit) | Write, rewrite, and validate git commit messages following the Conventional Commits specification | me |
| [`converge`](skills/converge) | Critique-loop with Cursor's `agent` CLI as a read-only second-agent reviewer across spec → plan → code phases | me |
| [`jina-reader`](skills/jina-reader) | Fetch any URL as clean Markdown or search the web with full content via Jina Reader | me |
| [`brainstorming`](skills/brainstorming) | Explore user intent, requirements, and design before implementation | [superpowers](licenses/superpowers/) |
| [`dispatching-parallel-agents`](skills/dispatching-parallel-agents) | Run independent tasks in parallel via subagents | [superpowers](licenses/superpowers/) |
| [`executing-plans`](skills/executing-plans) | Execute a written implementation plan with review checkpoints | [superpowers](licenses/superpowers/) |
| [`finishing-a-development-branch`](skills/finishing-a-development-branch) | Decide how to integrate completed work (merge, PR, or cleanup) | [superpowers](licenses/superpowers/) |
| [`receiving-code-review`](skills/receiving-code-review) | Process code review feedback rigorously, not performatively | [superpowers](licenses/superpowers/) |
| [`requesting-code-review`](skills/requesting-code-review) | Dispatch a code reviewer subagent on completed work | [superpowers](licenses/superpowers/) |
| [`subagent-driven-development`](skills/subagent-driven-development) | Execute plans with independent tasks via subagents in the current session | [superpowers](licenses/superpowers/) |
| [`systematic-debugging`](skills/systematic-debugging) | Debug bugs, test failures, and unexpected behavior systematically | [superpowers](licenses/superpowers/) |
| [`test-driven-development`](skills/test-driven-development) | Write tests before implementation | [superpowers](licenses/superpowers/) |
| [`using-git-worktrees`](skills/using-git-worktrees) | Create isolated workspaces for feature work | [superpowers](licenses/superpowers/) |
| [`using-superpowers`](skills/using-superpowers) | Meta-skill: how to find and use other skills | [superpowers](licenses/superpowers/) |
| [`verification-before-completion`](skills/verification-before-completion) | Run verification commands before claiming work complete | [superpowers](licenses/superpowers/) |
| [`writing-plans`](skills/writing-plans) | Turn a spec into a multi-step implementation plan | [superpowers](licenses/superpowers/) |
| [`writing-skills`](skills/writing-skills) | Create, edit, and verify skills | [superpowers](licenses/superpowers/) |

Scope membership lives in [`config.json`](config.json). `Source` links to the upstream's license and provenance; `me` means authored in this repo under [`LICENSE`](LICENSE).

## Configs

Global Claude Code config files (e.g. `~/.claude/CLAUDE.md`) are managed the same way: kept in [`home/`](home/), declared per-scope in [`config.json`](config.json) under `configs`, and symlinked into `~/.claude/` by `bin/install-config`.

| File | Description |
| --- | --- |
| [`home/CLAUDE.md`](home/CLAUDE.md) | Global instructions: SOUL, boundaries, git/worktree/safety preferences |

## Requirements

- `bash` (4+) and `jq` for the install/uninstall scripts.

Install `jq` on macOS with `brew install jq`.

## Installation

Symlink the skills into Claude Code's skills directory:

```bash
bin/install-skills                       # install all scopes (union)
bin/install-skills --scope personal      # install only "personal" scope
bin/install-skills --scope work          # install only "work" scope
bin/install-skills --dry-run             # preview without changes
bin/install-skills brainstorming foo     # install specific skills by name
bin/uninstall-skills                     # remove all symlinks for known skills
bin/uninstall-skills --scope work        # remove only one scope
bin/doctor                               # check local setup without changes
```

The script creates symlinks at `~/.claude/skills/<skill>` pointing into this repo. Output is one line per skill: `identical`, `linked`, `relinked`, `unlinked`, `skipped`, or `warning`.

Symlink the config files into `~/.claude/`:

```bash
bin/install-config                       # install all scopes (union)
bin/install-config --scope personal      # install only "personal" scope
bin/install-config --dry-run             # preview without changes
bin/install-config CLAUDE.md             # install specific files by name
bin/uninstall-config                     # remove all symlinks for known configs
```

If `~/.claude/<file>` already exists as a real file, it is moved to `<file>.bak.<timestamp>` before the symlink is created.

**Behavior notes:**
- If a target exists and is *not* a symlink, the script aborts with a warning. Resolve manually (rename or delete the real directory) and re-run.
- When `--scope` is given, symlinks for skills outside that scope (but still managed by this repo) are removed automatically. This makes scope-switching idempotent: running `--scope personal` then `--scope work` leaves only the work scope linked.
- Re-running after the repo has been moved to a new path will auto-relink stale symlinks to the new location.
- Skills not listed in any scope of `config.json` are ignored entirely.

## Maintenance

Procedure for adding, updating, removing, or moving skills (both self-authored
and external) is in [`docs/managing-skills.md`](docs/managing-skills.md). AI
agents working in this repo should read [`CLAUDE.md`](CLAUDE.md) first.

## Licenses

- Code authored in this repo: MIT (see [`LICENSE`](LICENSE)).
- Forked skills: retain their upstream licenses, included verbatim under [`licenses/`](licenses/).
