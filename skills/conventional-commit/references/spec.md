# Conventional Commits 1.0.0 — Full Specification

Source: https://www.conventionalcommits.org/en/v1.0.0/

## Formal Rules

Key words per RFC 2119: MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, OPTIONAL.

1. Commits MUST be prefixed with a type (noun: `feat`, `fix`, etc.), followed by the OPTIONAL scope, OPTIONAL `!`, and REQUIRED terminal colon and space.
2. `feat` MUST be used when a commit adds a new feature.
3. `fix` MUST be used when a commit represents a bug fix.
4. A scope MAY be provided after a type. A scope MUST consist of a noun describing a section of the codebase surrounded by parentheses, e.g. `fix(parser):`.
5. A description MUST immediately follow the colon and space after the type/scope prefix.
6. A longer commit body MAY be provided after the short description, starting one blank line after the description.
7. A commit body is free-form and MAY consist of any number of newline-separated paragraphs.
8. One or more footers MAY be provided one blank line after the body. Each footer MUST consist of a word token, followed by either a `:` or `#` separator, followed by a string value (inspired by git trailer convention).
9. A footer's token MUST use `-` in place of whitespace characters, e.g. `Acked-by`. Exception: `BREAKING CHANGE` MAY also be used as a token (with a space).
10. A footer's value MAY contain spaces and newlines; parsing MUST terminate when the next valid footer token/separator pair is observed.
11. Breaking changes MUST be indicated in the type/scope prefix (via `!`) or as an entry in the footer.
12. If included as a footer, a breaking change MUST consist of the uppercase text `BREAKING CHANGE`, followed by a colon, space, and description.
13. If `!` is used, `BREAKING CHANGE:` MAY be omitted from the footer; the commit description SHALL be used to describe the breaking change.
14. Types other than `feat` and `fix` MAY be used, e.g. `docs:`, `refactor:`.
15. Conventional Commits units MUST NOT be treated as case-sensitive, with the exception of `BREAKING CHANGE` which MUST be uppercase.
16. `BREAKING-CHANGE` MUST be synonymous with `BREAKING CHANGE` when used as a footer token.

## SemVer Mapping

| Commit | Version bump |
|--------|-------------|
| `fix` type | PATCH |
| `feat` type | MINOR |
| `BREAKING CHANGE` or `!` | MAJOR |

Breaking changes can appear on any type — e.g. `chore!:` still triggers a MAJOR bump.

## Common Extended Types (Angular convention)

`build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`

Not part of the core spec but widely adopted via `@commitlint/config-conventional`.

## Revert Commits

No formal spec definition. Recommended pattern:

```
revert: let us never again speak of the noodle incident

Refs: 676104e, a215868
```

## FAQ Highlights

- **Multiple types apply?** → Split into multiple commits.
- **Wrong type used?** → Before merge: `git rebase -i` to fix. After release: it's not the end of the world.
- **All contributors need to follow this?** → No. Squash workflows let maintainers clean up on merge.
- **Casing?** → Any consistent casing. Lowercase recommended.
