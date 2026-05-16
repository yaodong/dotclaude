---
name: conventional-commit
description: Write and validate git commit messages following Conventional Commits spec.
license: MIT
compatibility: No external dependencies
metadata:
  author: yaodong
  version: "1.0"
---

# Conventional Commit

Write and validate commit messages following [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

## Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Types

| Type | SemVer | Use when |
|------|--------|----------|
| `feat` | MINOR | Adding a new feature |
| `fix` | PATCH | Patching a bug |
| `docs` | — | Documentation only |
| `style` | — | Formatting, whitespace — no logic change |
| `refactor` | — | Refactor with no feature/fix |
| `perf` | — | Performance improvement |
| `test` | — | Adding or fixing tests |
| `build` | — | Build system or dependency changes |
| `ci` | — | CI configuration |
| `chore` | — | Maintenance, no production code change |
| `revert` | — | Reverting a prior commit |

## Breaking Changes → MAJOR

Two equivalent forms — use either or both:

```
feat!: remove deprecated v1 endpoints
```

```
feat: remove deprecated v1 endpoints

BREAKING CHANGE: /v1/* routes are removed. Migrate to /v2/*.
```

## Workflow

1. **Understand the change** — read the diff, PR description, or user's summary
2. **Pick type** — what is the primary intent? Bug fix → `fix`, new capability → `feat`, etc.
3. **Pick scope** (optional) — the affected module, package, or component in parentheses
4. **Write the description** — imperative mood, lowercase, no trailing period, ≤72 chars total for subject line
5. **Add body if needed** — explain *why*, not *what* (the diff shows what); blank line after description
6. **Add footers if needed** — `BREAKING CHANGE:`, `Refs: #123`, `Closes: #456`; blank line after body

## Rules (quick ref)

- Type is **required**; lowercase preferred; be consistent
- Description **must** immediately follow `type[scope]: `
- Scope is a noun in parentheses: `fix(auth):`, `feat(api):`
- Body and footers are optional; each separated by a blank line
- Footer tokens use `-` instead of spaces (e.g. `Reviewed-by:`); exception: `BREAKING CHANGE`
- `BREAKING CHANGE` footer must be uppercase

## Examples

**Simple:**
```
docs: fix typo in README
```

**With scope:**
```
feat(lang): add Polish language support
```

**With body and footer:**
```
fix(auth): prevent token expiry race condition

Token refresh was triggered after the expiry check but before the
guarded request, causing intermittent 401s under high load.

Refs: #88
```

**Breaking change:**
```
feat(api)!: remove deprecated v1 endpoints

BREAKING CHANGE: /v1/* routes have been removed. Migrate to /v2/*.
```

**Revert:**
```
revert: let us never again speak of the noodle incident

Refs: 676104e, a215868
```

**Converting past-tense to conventional:**
- `"Added login page"` → `feat: add login page`
- `"Fixed null pointer bug"` → `fix: resolve null pointer in user service`
- `"Updated docs"` → `docs: update authentication guide`

## Edge cases

For precise spec rules (footer parsing, multi-paragraph bodies, case sensitivity),
see [references/spec.md](references/spec.md).
