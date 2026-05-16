# Managing Skills

The single procedure for adding, updating, removing, or relocating skills in
this repo. Covers both self-authored and externally-forked skills.

## Principles

1. **The repo is the source of truth.** `~/.claude/skills/<name>` is a symlink
   into `skills/<name>` here. Edits happen in this repo, never in the symlink
   target.
2. **README lists every skill; `config.json` controls scope.** Adding or
   removing a skill updates both. Rescoping touches only `config.json`.
3. **Trust no upstream by default.** External skills go through security and
   dependency review before adoption. No "convenience installers."
4. **Pin versions.** External skills are frozen at the imported version.
   Updates are explicit, not automatic.
5. **No new runtime deps.** Scripts in `bin/` rely on `bash` + `jq` only. Keep
   it that way.

---

## Common steps (apply to every flow)

These are the mechanical pieces shared across personal and external skills.
The flow-specific sections below tell you when to invoke them.

### Add to `config.json`

Choose a scope (`personal`, `work`, or add a new key). Add the skill name to
the appropriate scope array. Keep arrays alphabetically sorted.

### Update the README master table

Add a row with: skill name (linked to its directory), description, source.

`Source` is `me` for self-authored, or a link to `licenses/<project>/` for
forks.

### Run the install script

```bash
bin/install-skills
```

The script is idempotent. Output should show `linked` for the new skill,
`identical` for everything else.

### Verify

```bash
ls -la ~/.claude/skills/<name>     # symlink exists, resolves into this repo
head -5 ~/.claude/skills/<name>/SKILL.md   # file is readable through the link
```

---

## Flow A: Adding a self-authored skill

Use when the user authored the skill themselves (or wants to start fresh in
this repo).

### Step 1: Place the skill files

If the skill exists outside the repo (e.g., a real directory in
`~/.claude/skills/`), move it in:

```bash
mv ~/.claude/skills/<name> skills/<name>
```

If creating from scratch, make the directory and write at minimum a
`SKILL.md` with valid YAML frontmatter (`name`, `description`).

If the skill was previously a real directory in `~/.claude/skills/`, that
directory no longer exists after the move. The install script will create the
symlink in step 4.

### Step 2: Update `config.json`

Add the skill name to the appropriate scope.

### Step 3: Update the README master table

Add a row. Source = `me`.

### Step 4: Install + verify

```bash
bin/install-skills
ls -la ~/.claude/skills/<name>
```

### Step 5: Commit

```
feat: add <name> skill
```

---

## Flow B: Adding an external skill

Use when adopting a skill authored by someone else. Security is the priority.

### Step 1: Download to a scratch location

Clone or download the upstream into `~/Downloads/<project>-downloaded` or
similar. **Do not extract into this repo or `~/.claude/`.**

### Step 2: Inspect the upstream layout

List the top level. Identify what's actually in there:

- `skills/` folders — adoption candidates
- `hooks/`, `.claude-plugin/`, `plugin.json`, marketplace metadata — behavior
  modification, treat with suspicion
- `scripts/`, `tools/`, `bin/` — maintainer tooling, usually skip
- `assets/`, `docs/`, `tests/` — usually skip
- `LICENSE`, `NOTICE` — required for attribution

### Step 3: Security check (MANDATORY)

Before reading any markdown, check what would actually execute.

**Search for network calls:**

```bash
grep -rE "curl|wget|http://|https://|fetch\(|urllib|requests\.|axios" \
  <download>/skills/ <download>/hooks/ 2>&1
```

Categorize each hit:
- Documentation links in markdown → fine
- Example strings inside skill text → fine
- Localhost / `127.0.0.1` bindings in scripts → local only, low risk
- Outbound HTTP from a script → flag and review with the user
- Telemetry / analytics calls → refuse adoption

**Find executables and read them:**

```bash
find <download>/skills -type f \
  \( -name "*.sh" -o -name "*.py" -o -name "*.js" \
  -o -name "*.cjs" -o -name "*.ts" \)
```

For each: read what it imports, what it does, where it sends data. Servers
that bind to `127.0.0.1` are local. Anything calling out needs explicit
approval.

**Read every hook line by line.** Hooks run unconditionally and silently. The
user should see what gets injected before adoption.

### Step 4: Dependency check (MANDATORY)

Find runtime dependencies:

```bash
find <download> -name "package.json" -not -path "*/node_modules/*"
find <download> -name "requirements.txt" -o -name "pyproject.toml"
grep -ri "requires:\|depends:\|prerequisite" <download>/skills/
```

Report findings to the user. **Do not run** `npm install`, `pip install`,
`brew install`, or any package manager without explicit approval (see global
CLAUDE.md).

### Step 5: Compare against existing skills

If the user already has skills with the same name, diff them:

```bash
for s in skills/*/; do
  name=$(basename "$s")
  [ -d "<download>/skills/$name" ] && diff -rq "$s" "<download>/skills/$name"
done
```

Decide per-skill: refresh, keep current, or merge.

### Step 6: Get approval

Present the user with:
- Candidate skill list with descriptions
- Anything flagged in security/dependency check
- Diff summary if existing skills overlap
- **Explicit list of files NOT being installed** (hooks, plugin metadata,
  scripts, etc.) with reasons

Wait for explicit approval per skill. Do not proceed on assumed consent.

### Step 7: Set up attribution

```bash
mkdir -p licenses/<project>
cp <download>/LICENSE licenses/<project>/LICENSE
```

Write `licenses/<project>/README.md`:

```markdown
# <upstream-name>

Upstream: <URL>
Version: <version-or-commit>
License: <SPDX-id> (see [`LICENSE`](LICENSE))
Imported: <YYYY-MM-DD>

## Skills forked from this project

- <skill-1>
- <skill-2>

Local modifications: none yet (verbatim fork).
```

### Step 8: Copy approved skills

```bash
for name in <approved-skill-names>; do
  cp -R <download>/skills/$name skills/$name
done
```

### Step 9: Update `config.json`

Add each skill to the appropriate scope.

### Step 10: Update the README master table

Add a row per skill. Source links to `licenses/<project>/`.

### Step 11: Install + verify

```bash
bin/install-skills
ls -la ~/.claude/skills/
head -5 ~/.claude/skills/<one-of-them>/SKILL.md
```

### Step 12: Commit

```
feat: add <N> skills forked from <project> v<version>
```

---

## Flow C: Updating an external skill

Use when refreshing forks against a newer upstream version.

### Step 1: Download the new version

Same as Flow B Step 1 — to a scratch path.

### Step 2: Diff against current

```bash
# List forked skills from licenses/<project>/README.md, then:
for name in <forked-skills>; do
  diff -rq skills/$name <download>/skills/$name
done
```

### Step 3: Read release notes

Check upstream's `RELEASE-NOTES.md` / `CHANGELOG.md` for changes since the
version recorded in `licenses/<project>/README.md`.

### Step 4: Re-run security check

Run the Flow B Step 3 commands against the new download. Pay special
attention to **newly added** hooks, scripts, or network calls that weren't in
the prior version.

### Step 5: Get approval

Show the user:
- Per-skill diff summary
- Release notes summary
- Anything new in security/dependency surface
- Recommendation: refresh all, refresh some, or skip this update

### Step 6: Apply approved changes

```bash
cp <download>/skills/<name>/SKILL.md skills/<name>/SKILL.md
# or full directory copy if many files changed:
rm -rf skills/<name> && cp -R <download>/skills/<name> skills/<name>
```

### Step 7: Update `licenses/<project>/README.md`

Bump version. Update import date. Note any local modifications. Update skill
list if skills were added or removed upstream.

### Step 8: Update README master table if descriptions changed.

### Step 9: Re-run install (optional)

`bin/install-skills` is idempotent. Re-run only if:
- The repo path changed (auto-relink)
- New skills were added (need new symlinks)
- Skills were removed (run `bin/uninstall-skills <name>` first)

### Step 10: Commit

```
chore: update <project> skills to v<new-version>
```

---

## Flow D: Removing a skill

```bash
bin/uninstall-skills <name>      # remove the symlink
rm -rf skills/<name>             # remove the source
```

Then update:
- `config.json` (remove from any scope)
- README master table (delete the row)
- If forked: `licenses/<project>/README.md` skill list
- If it was the last skill from `<project>`: `rm -rf licenses/<project>/`

Commit.

---

## Flow E: Moving a skill between scopes

Edit `config.json` only. Move the name from one scope array to another. The
README does not track scope.

Re-run `bin/install-skills --scope <new-scope>` if you want only the new
scope active right now. Otherwise the union is still installed and nothing
visible changes — but the next `--scope <old-scope>` run will correctly
unlink the moved skill.

Commit.

---

## Flow F: Managing a config file in `home/`

Use when adding, updating, or removing a file that gets symlinked into
`~/.claude/` (e.g. `CLAUDE.md`).

### Add a new config file

1. Place the file at `home/<name>` (e.g. `home/CLAUDE.md`).
2. Add `<name>` to the appropriate scope under `.configs` in `config.json`.
   Scope arrays are kept alphabetically sorted.
3. Add a row to the README "Configs" table.
4. Run `bin/install-config` and verify with `ls -la ~/.claude/<name>`.
5. Commit.

### Update an existing config file

Edit `home/<name>` directly. The symlink already points into the repo, so
changes take effect immediately. No reinstall needed unless the repo path
changed.

### Remove a config file

```bash
bin/uninstall-config <name>
rm home/<name>
```

Then update `config.json` (remove from any scope) and the README. Commit.

### Notes

- `bin/install-config` is idempotent. Output: `identical`, `linked`,
  `relinked`, `backed-up`, `unlinked`, or `missing`.
- If `~/.claude/<name>` already exists as a real file (not a symlink), the
  installer moves it to `<name>.bak.<timestamp>` before linking. Review and
  delete the backup once you've confirmed nothing was lost.
- Config files at `home/` are flat — no subdirectories supported by the
  current installer.

---

## Things to refuse

- Adopting external hooks without line-by-line review.
- Running upstream's `install.sh` or any "convenience" installer.
- Running `npm install` / `pip install` / `brew install` to satisfy upstream
  runtime deps without explicit approval.
- Copying upstream's `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` to the user's
  global config (would override their preferences).
- Pushing commits without approval.
- Adopting a skill that contains telemetry, analytics, or external service
  callbacks unless the user explicitly accepts.

## Things that are usually fine

- Reading every file in the download for understanding.
- Local-only scripts (bind to `127.0.0.1`, no outbound network).
- Skills that shell out to common system tools (`git`, `bash`, `node`, `dot`,
  etc.).
- Updating SKILL.md text, examples, or frontmatter in self-authored skills.
- Re-running `bin/install-skills` (idempotent).

---

## Repo-relocation note

The install/uninstall scripts compute paths from their own location at
runtime (`$(dirname "$0")/..`), so moving the repo to a new path is simple:

1. Move/rename the repo.
2. Run `bin/install-skills` from the new location. Symlinks pointing into the
   old (now-missing) repo path will be auto-relinked to the new path.

The script handles this case explicitly — output shows `relinked` for any
symlinks that were updated.
