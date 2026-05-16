#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""
Jina Reader — fetch any URL as clean Markdown, or search the web with full content.

Usage:
  fetch:   python3 scripts/jina.py fetch <url> [--format markdown|text|html] [--no-images] [--timeout 30]
  search:  python3 scripts/jina.py search "<query>" [--site domain] [--timeout 30]
"""

import argparse
import sys
import urllib.parse

try:
    import requests
except ImportError:
    print("Missing dependency: pip install requests", file=sys.stderr)
    sys.exit(1)

READER_BASE = "https://r.jina.ai/"
SEARCH_BASE = "https://s.jina.ai/"


def fetch_url(url: str, fmt: str = "markdown", no_images: bool = False, timeout: int = 30) -> str:
    target = READER_BASE + url
    headers = {
        "Accept": "text/plain",
        "X-Return-Format": fmt,
    }
    if no_images:
        headers["X-Remove-Selector"] = "img, picture, figure"
    resp = requests.get(target, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def search_web(query: str, sites: list[str] | None = None, timeout: int = 30) -> str:
    params = urllib.parse.urlencode(
        [("site", s) for s in (sites or [])], doseq=True
    )
    target = SEARCH_BASE + urllib.parse.quote(query) + (f"?{params}" if params else "")
    headers = {
        "Accept": "text/plain",
        "X-Return-Format": "markdown",
    }
    resp = requests.get(target, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def main():
    parser = argparse.ArgumentParser(description="Jina Reader — URL to Markdown / Web Search")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="Fetch a URL as clean Markdown")
    p_fetch.add_argument("url", help="URL to fetch")
    p_fetch.add_argument("--format", choices=["markdown", "text", "html"], default="markdown")
    p_fetch.add_argument("--no-images", action="store_true", help="Strip images from output")
    p_fetch.add_argument("--timeout", type=int, default=30)

    p_search = sub.add_parser("search", help="Search the web via Jina (returns top 5 full-content results)")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--site", action="append", dest="sites", metavar="DOMAIN", help="Restrict to domain (repeatable)")
    p_search.add_argument("--timeout", type=int, default=30)

    args = parser.parse_args()

    try:
        if args.command == "fetch":
            result = fetch_url(args.url, fmt=args.format, no_images=args.no_images, timeout=args.timeout)
        else:
            result = search_web(args.query, sites=args.sites, timeout=args.timeout)
    except requests.HTTPError as e:
        print(f"HTTP {e.response.status_code}: {e.response.text[:200]}", file=sys.stderr)
        sys.exit(1)
    except requests.Timeout:
        print(f"Timeout after {args.timeout}s — try --timeout with a higher value", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
