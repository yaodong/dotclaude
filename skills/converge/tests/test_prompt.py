from converge.prompt import format_iterate_prompt


def test_message_only_when_no_files():
    out = format_iterate_prompt("just a question", [])
    assert out == "just a question"


def test_single_file_includes_contexts_block():
    out = format_iterate_prompt(
        "review please",
        ["/Users/me/proj/spec.md"],
    )
    assert out.startswith("review please\n\nContexts:\n")
    assert " - spec.md: /Users/me/proj/spec.md" in out


def test_multiple_files_listed():
    out = format_iterate_prompt(
        "review",
        ["/a/spec.md", "/b/plan.md"],
    )
    assert " - spec.md: /a/spec.md" in out
    assert " - plan.md: /b/plan.md" in out


def test_relative_paths_passed_through_unchanged():
    # Spec says Claude is responsible for absolutes; if it passes a relative
    # path, the formatter does not transform it — Cursor will fail to read.
    # This is intentional. The test pins the contract.
    out = format_iterate_prompt("m", ["docs/spec.md"])
    assert " - spec.md: docs/spec.md" in out
