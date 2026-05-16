# my-agents

Curated skill library for Claude Code. See [README.md](README.md) for what's
included and how to install.

## When asked to add or change a skill or config file, READ THIS FIRST

[`docs/managing-skills.md`](docs/managing-skills.md) — the single procedure
for adding, updating, removing, or moving skills (Flows A–E) and managing
files under `home/` symlinked into `~/.claude/` (Flow F).

## Hard rules

- **External skills require security + dependency check before adoption.**
  No exceptions. See managing-skills.md Flow B.
- **Don't edit forked SKILL.md files** without recording the change in
  `licenses/<project>/README.md` under "Local modifications".
- **`config.json` is the source of truth for scopes** — both `.scopes`
  (skills) and `.configs` (files in `home/`). When adding or removing
  either, update `config.json` and the relevant README table in the same
  commit. Rescoping only touches `config.json`.
- **Re-run `bin/install-skills` / `bin/install-config`** after touching
  `config.json`, `skills/`, or `home/`.
- **No new runtime dependencies** beyond `bash` + `jq`.
- **No auto-execution at clone time.** The repo never runs anything on its
  own — installation is always an explicit `bin/install-*` invocation. This
  preserves the opt-in property even though the installed config files
  (e.g. `home/CLAUDE.md`) themselves shape Claude's runtime behavior.

## Layout reference

- `skills/` — one subdirectory per skill, flat. Forked skills sit at the same
  path as upstream so diffs stay clean.
- `home/` — flat directory of files symlinked into `~/.claude/` (e.g.
  `CLAUDE.md`). One file = one symlink. No subdirectories.
- `config.json` — scope manifests for `.scopes` (skills) and `.configs`
  (home files). Personal, work, etc.
- `bin/` — install/uninstall scripts (POSIX bash + `jq`).
- `licenses/<project>/` — verbatim upstream `LICENSE` plus a `README.md`
  recording source URL, version, import date, and forked skill list.
- `docs/` — procedures for managing skills and configs.

## Conventions

- Master skills table in [README.md](README.md) lists every skill with its
  description and source. Scope membership is in `config.json` only.
- Scope arrays in `config.json` are kept alphabetically sorted.
- Commit messages follow Conventional Commits (see the `conventional-commit`
  skill in this repo).
- Don't push commits without explicit approval.
