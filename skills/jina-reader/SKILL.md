---
name: jina-reader
description: Fetch any URL as clean LLM-friendly Markdown, or search the web and get full content from top results — using Jina Reader (r.jina.ai / s.jina.ai). Use when you need to read a webpage, article, documentation, or PDF from a URL, or when searching the web and need actual page content (not just titles/snippets). Triggers on "fetch this URL", "read this page", "what does this page say", "search the web for", "get the content of", "extract text from".
license: MIT
compatibility: Requires Python 3.11+ and uv (or pip install requests)
metadata:
  author: yaodong
  version: "1.1"
---

# Jina Reader

Converts any URL to clean Markdown and searches the web with full content retrieval. No API key required.

## Workflow

**Fetch a URL:**
1. Identify the URL from the request
2. Run `scripts/jina.py fetch <url>`
3. Present extracted content

**Search the web:**
1. Identify the query (and optional site restrictions)
2. Run `scripts/jina.py search "<query>"`
3. Present top results with full content

## Usage

```bash
# Fetch a URL as Markdown
uv run --script scripts/jina.py fetch https://example.com

# Fetch as plain text
uv run --script scripts/jina.py fetch https://example.com --format text

# Strip images
uv run --script scripts/jina.py fetch https://example.com --no-images

# Search the web (returns top 5 results with full content)
uv run --script scripts/jina.py search "your query"

# Restrict search to specific domains
uv run --script scripts/jina.py search "your query" --site docs.python.org --site github.com
```

## Parameters

### fetch

| Parameter | Default | Description |
|---|---|---|
| `url` | required | URL to fetch |
| `--format` | `markdown` | Output format: `markdown`, `text`, `html` |
| `--no-images` | false | Strip images from output |
| `--timeout` | 30 | Request timeout in seconds |

### search

| Parameter | Default | Description |
|---|---|---|
| `query` | required | Search query |
| `--site` | — | Restrict to domain (repeatable) |
| `--timeout` | 30 | Request timeout in seconds |

## Output Contract

| Scenario | stdout | stderr | exit code |
|---|---|---|---|
| Success | Markdown content | (empty) | 0 |
| Invalid / unreachable URL | (empty) | Error message | 1 |
| HTTP error | (empty) | HTTP status + details | 1 |
| Timeout | (empty) | Timeout message | 1 |

## Notes

- PDFs are supported via `r.jina.ai`
- Responses are cached for 3600s by default
- For advanced headers (cookies, proxy, CSS selectors), see [references/api.md](references/api.md)
