#!/usr/bin/env python3
"""Bitbucket Cloud REST API helper for pull-request operations.

Auth: env vars BITBUCKET_EMAIL and BITBUCKET_API_TOKEN (Basic auth).
Workspace and repo slug are derived from `git remote get-url origin`.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


API_ROOT = "https://api.bitbucket.org/2.0"
DEFAULT_LIST_LIMIT = 25


class BitbucketError(RuntimeError):
    pass


def _auth_header() -> str:
    email = os.environ.get("BITBUCKET_EMAIL")
    token = os.environ.get("BITBUCKET_API_TOKEN")
    if not email or not token:
        raise BitbucketError(
            "Set BITBUCKET_EMAIL and BITBUCKET_API_TOKEN. Create a token at "
            "https://id.atlassian.com/manage-profile/security/api-tokens "
            "with the 'Pull requests: write' scope on the target repo."
        )
    raw = f"{email}:{token}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _explain_http_error(method: str, url: str, code: int, detail: str) -> str:
    if code == 401:
        return (
            f"{method} {url} -> 401 Unauthorized. "
            "Check BITBUCKET_EMAIL and BITBUCKET_API_TOKEN. "
            "Token may be expired or revoked.\n" + detail
        )
    if code == 403:
        return (
            f"{method} {url} -> 403 Forbidden. "
            "Token is likely missing the 'Pull requests: write' scope on this repo, "
            "or the user lacks repo permissions.\n" + detail
        )
    if code == 404:
        return (
            f"{method} {url} -> 404 Not Found. "
            "PR/repo doesn't exist, or the token can't see it (private repo + wrong scope).\n"
            + detail
        )
    return f"{method} {url} -> HTTP {code}\n{detail}"


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    url = path if path.startswith("http") else f"{API_ROOT}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", _auth_header())
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read().decode()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise BitbucketError(_explain_http_error(method, url, e.code, detail)) from None
    except urllib.error.URLError as e:
        raise BitbucketError(f"{method} {url} failed: {e.reason}") from None


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _parse_workspace_repo(remote_url: str) -> tuple[str, str]:
    # git@bitbucket.org:workspace/repo.git  OR  https://bitbucket.org/workspace/repo.git
    m = re.search(r"bitbucket\.org[:/]([^/]+)/([^/]+?)(?:\.git)?$", remote_url)
    if not m:
        raise BitbucketError(f"Cannot parse workspace/repo from remote: {remote_url}")
    return m.group(1), m.group(2)


def repo_coords(workspace: str | None, repo: str | None) -> tuple[str, str]:
    if workspace and repo:
        return workspace, repo
    remote = _git("remote", "get-url", "origin")
    return _parse_workspace_repo(remote)


def current_branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD")


def default_branch(workspace: str, repo: str) -> str:
    info = _request("GET", f"/repositories/{workspace}/{repo}")
    return info.get("mainbranch", {}).get("name", "master")


def read_body(text: str | None, file: str | None) -> str:
    if file == "-":
        return sys.stdin.read()
    if file:
        with open(file, "r") as f:
            return f.read()
    return text or ""


def _edit_in_editor(initial: str, hint_header: str = "") -> str:
    """Open $EDITOR with `initial` (and optional comment header), return saved content.

    Lines starting with '#' at the top of the file are stripped after save.
    Returns the trimmed body.
    """
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        path = f.name
        if hint_header:
            for line in hint_header.splitlines():
                f.write(line + "\n" if line.startswith("#") else f"# {line}\n")
            f.write("#\n")
        f.write(initial)
    try:
        subprocess.run([editor, path], check=True)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    finally:
        os.unlink(path)
    lines = content.splitlines(keepends=True)
    out: list[str] = []
    in_header = bool(hint_header)
    for line in lines:
        if in_header and line.startswith("#"):
            continue
        in_header = False
        out.append(line)
    return "".join(out).strip()


def _resolve_body(
    args: argparse.Namespace,
    *,
    initial_for_edit: str = "",
    edit_hint: str = "",
    require: bool = True,
) -> str:
    """Return body text from --description / --description-file / --edit."""
    if getattr(args, "edit", False):
        body = _edit_in_editor(initial_for_edit, edit_hint)
        if not body and initial_for_edit.strip():
            raise BitbucketError("Editor exited with no changes; aborting.")
        if not body:
            raise BitbucketError("Editor exited with empty content; aborting.")
        return body
    body = read_body(getattr(args, "description", None), getattr(args, "description_file", None))
    if require and not body:
        raise BitbucketError("Provide -d, -F, or --edit.")
    return body


def _commits_summary(source: str, destination: str) -> str:
    try:
        return _git(
            "log", "--no-merges", "--pretty=format:%h %s",
            f"{destination}..{source}",
        )
    except subprocess.CalledProcessError:
        return ""


def cmd_create(args: argparse.Namespace) -> None:
    workspace, repo = repo_coords(args.workspace, args.repo)
    source = args.source or current_branch()
    destination = args.destination or default_branch(workspace, repo)
    hint = (
        f"Source:      {source}\n"
        f"Destination: {destination}\n"
        f"\nCommits to be included:\n"
        f"{_commits_summary(source, destination) or '(none found)'}\n"
        f"\nLines starting with '#' will be removed."
    )
    description = _resolve_body(
        args, initial_for_edit="", edit_hint=hint, require=False
    )
    body: dict[str, Any] = {
        "title": args.title,
        "source": {"branch": {"name": source}},
        "destination": {"branch": {"name": destination}},
        "description": description,
        "close_source_branch": args.close_source_branch,
    }
    if args.reviewer:
        body["reviewers"] = [
            {"uuid": r} if r.startswith("{") else {"username": r}
            for r in args.reviewer
        ]
    pr = _request("POST", f"/repositories/{workspace}/{repo}/pullrequests", body)
    print(json.dumps({"id": pr["id"], "url": pr["links"]["html"]["href"]}, indent=2))


def cmd_update_description(args: argparse.Namespace) -> None:
    workspace, repo = repo_coords(args.workspace, args.repo)
    initial = ""
    if args.edit:
        current = _request(
            "GET", f"/repositories/{workspace}/{repo}/pullrequests/{args.id}"
        )
        initial = current.get("description", "") or ""
    description = _resolve_body(args, initial_for_edit=initial, edit_hint="")
    pr = _request(
        "PUT",
        f"/repositories/{workspace}/{repo}/pullrequests/{args.id}",
        {"description": description},
    )
    print(json.dumps({"id": pr["id"], "url": pr["links"]["html"]["href"]}, indent=2))


def cmd_update_title(args: argparse.Namespace) -> None:
    workspace, repo = repo_coords(args.workspace, args.repo)
    if args.edit:
        current = _request(
            "GET", f"/repositories/{workspace}/{repo}/pullrequests/{args.id}"
        )
        title = _edit_in_editor(current.get("title", ""), "")
        if not title:
            raise BitbucketError("Editor exited with empty title; aborting.")
    else:
        title = args.title
    pr = _request(
        "PUT",
        f"/repositories/{workspace}/{repo}/pullrequests/{args.id}",
        {"title": title},
    )
    print(json.dumps({"id": pr["id"], "url": pr["links"]["html"]["href"]}, indent=2))


def cmd_comment(args: argparse.Namespace) -> None:
    workspace, repo = repo_coords(args.workspace, args.repo)
    text = _resolve_body(args, initial_for_edit="", edit_hint="")
    res = _request(
        "POST",
        f"/repositories/{workspace}/{repo}/pullrequests/{args.id}/comments",
        {"content": {"raw": text}},
    )
    print(json.dumps({"id": res["id"], "pr": args.id}, indent=2))


def cmd_merge(args: argparse.Namespace) -> None:
    workspace, repo = repo_coords(args.workspace, args.repo)
    body: dict[str, Any] = {"merge_strategy": args.strategy}
    if args.message:
        body["message"] = args.message
    if args.close_source_branch:
        body["close_source_branch"] = True
    pr = _request(
        "POST",
        f"/repositories/{workspace}/{repo}/pullrequests/{args.id}/merge",
        body,
    )
    print(json.dumps(
        {"id": pr["id"], "state": pr.get("state"), "url": pr["links"]["html"]["href"]},
        indent=2,
    ))


def _format_reviewers(pr: dict[str, Any]) -> str:
    participants = pr.get("participants", []) or []
    reviewers = [p for p in participants if p.get("role") == "REVIEWER"]
    if not reviewers:
        return "(none)"
    parts = []
    for r in reviewers:
        name = r.get("user", {}).get("display_name", "?")
        mark = "approved" if r.get("approved") else "pending"
        parts.append(f"{name} [{mark}]")
    return ", ".join(parts)


def cmd_view(args: argparse.Namespace) -> None:
    workspace, repo = repo_coords(args.workspace, args.repo)
    pr = _request("GET", f"/repositories/{workspace}/{repo}/pullrequests/{args.id}")
    if args.json:
        print(json.dumps(pr, indent=2))
        return
    print(f"#{pr['id']}  {pr['title']}")
    print(f"  state:     {pr['state']}")
    print(f"  author:    {pr['author']['display_name']}")
    print(f"  source:    {pr['source']['branch']['name']}")
    print(f"  dest:      {pr['destination']['branch']['name']}")
    print(f"  reviewers: {_format_reviewers(pr)}")
    if pr.get("merge_commit"):
        print(f"  merged:    {pr['merge_commit'].get('hash', '?')}")
    print(f"  url:       {pr['links']['html']['href']}")
    print()
    print(pr.get("description", "") or "(no description)")


def cmd_list(args: argparse.Namespace) -> None:
    workspace, repo = repo_coords(args.workspace, args.repo)
    params: list[tuple[str, str]] = [("state", args.state)]
    if args.branch:
        params.append(("q", f'source.branch.name="{args.branch}"'))
    qs = urllib.parse.urlencode(params)
    next_url: str | None = f"/repositories/{workspace}/{repo}/pullrequests?{qs}"
    shown = 0
    total: int | None = None
    while next_url and shown < args.limit:
        page = _request("GET", next_url)
        if total is None:
            total = page.get("size")
        for pr in page.get("values", []):
            if shown >= args.limit:
                break
            print(
                f"#{pr['id']}\t{pr['state']}\t"
                f"{pr['source']['branch']['name']} -> {pr['destination']['branch']['name']}\t"
                f"{pr['title']}"
            )
            shown += 1
        next_url = page.get("next") if shown < args.limit else None
    if total is not None and total > shown:
        print(f"(+{total - shown} more — re-run with --limit {total})", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Bitbucket Cloud PR helper")
    p.add_argument("--workspace", help="Override workspace (default: parsed from origin)")
    p.add_argument("--repo", help="Override repo slug (default: parsed from origin)")
    sub = p.add_subparsers(dest="command", required=True)

    def _add_body_flags(sp: argparse.ArgumentParser, *, required: bool) -> None:
        g = sp.add_mutually_exclusive_group(required=required)
        g.add_argument("-d", "--description", help="Body as a string")
        g.add_argument("-F", "--description-file", help="Read body from file ('-' for stdin)")
        g.add_argument("--edit", action="store_true", help="Open $EDITOR to compose body")

    c = sub.add_parser("create", help="Create a pull request")
    c.add_argument("-t", "--title", required=True)
    _add_body_flags(c, required=False)
    c.add_argument("-s", "--source", help="Source branch (default: current branch)")
    c.add_argument("-D", "--destination", help="Destination branch (default: repo main branch)")
    c.add_argument(
        "--reviewer", action="append", default=[],
        help="Reviewer UUID (preferred, in {braces}) or username; repeatable"
    )
    c.add_argument("--close-source-branch", action="store_true")
    c.set_defaults(func=cmd_create)

    u = sub.add_parser("update-description", help="Replace the description of an existing PR")
    u.add_argument("id", type=int)
    _add_body_flags(u, required=True)
    u.set_defaults(func=cmd_update_description)

    t = sub.add_parser("update-title", help="Replace the title of an existing PR")
    t.add_argument("id", type=int)
    g = t.add_mutually_exclusive_group(required=True)
    g.add_argument("-t", "--title")
    g.add_argument("--edit", action="store_true", help="Open $EDITOR pre-filled with current title")
    t.set_defaults(func=cmd_update_title)

    cm = sub.add_parser("comment", help="Add a top-level comment to a PR")
    cm.add_argument("id", type=int)
    _add_body_flags(cm, required=True)
    cm.set_defaults(func=cmd_comment)

    m = sub.add_parser("merge", help="Merge a PR")
    m.add_argument("id", type=int)
    m.add_argument(
        "--strategy", default="merge_commit",
        choices=["merge_commit", "squash", "fast_forward"],
    )
    m.add_argument("--message", help="Override merge commit message")
    m.add_argument("--close-source-branch", action="store_true")
    m.set_defaults(func=cmd_merge)

    v = sub.add_parser("view", help="View a PR")
    v.add_argument("id", type=int)
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_view)

    l = sub.add_parser("list", help="List PRs")
    l.add_argument("--state", default="OPEN", choices=["OPEN", "MERGED", "DECLINED", "SUPERSEDED"])
    l.add_argument("--branch", help="Filter by source branch name")
    l.add_argument(
        "--limit", type=int, default=DEFAULT_LIST_LIMIT,
        help=f"Max results (default: {DEFAULT_LIST_LIMIT})",
    )
    l.set_defaults(func=cmd_list)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except BitbucketError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip() if isinstance(e.stderr, str) else ""
        print(f"git error: {stderr or e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
