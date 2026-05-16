# Jina Reader API Reference

## Endpoints

| Endpoint | Purpose |
|---|---|
| `https://r.jina.ai/<url>` | Convert URL to Markdown |
| `https://s.jina.ai/<query>` | Web search with full content |

## Request Headers

| Header | Values | Notes |
|---|---|---|
| `X-Return-Format` | `markdown`, `text`, `html`, `screenshot` | Default: markdown |
| `X-No-Cache` | `true` | Bypass 3600s cache |
| `X-Cache-Tolerance` | integer (seconds) | Custom cache tolerance |
| `X-With-Generated-Alt` | `true` | Caption images (off by default for latency) |
| `X-Target-Selector` | CSS selector | Focus on a specific element |
| `X-Wait-For-Selector` | CSS selector | Wait for element before extracting |
| `X-Set-Cookie` | cookie string | Forward cookies; disables caching |
| `X-Proxy-URL` | proxy URL | Route request through proxy |
| `X-Respond-With` | `markdown`, `html`, `text`, `screenshot` | Bypass readability filtering |

## Search Parameters

- `site=<domain>` — restrict search to one or more domains (repeatable)

Example: `https://s.jina.ai/query?site=docs.python.org&site=github.com`

## Rate Limits

- Free tier: no API key required, rate-limited
- Paid tier: add `Authorization: Bearer <token>` for higher limits
- Details: https://jina.ai/reader#pricing
