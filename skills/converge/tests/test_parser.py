import pytest

from converge.parser import parse_status


@pytest.mark.parametrize("reply,expected", [
    ("Looks good.\n\nSTATUS: APPROVED", "approved"),
    ("Some notes.\n\nSTATUS: CHANGES_REQUESTED", "changes_requested"),
    ("I have questions.\n\nSTATUS: NEEDS_INFO", "needs_info"),
    ("STATUS: APPROVED", "approved"),
    ("status: approved", "approved"),  # case-insensitive
    ("STATUS:    APPROVED   ", "approved"),  # extra whitespace
    ("STATUS: APPROVED\n\n", "approved"),  # trailing newlines
])
def test_recognized_statuses(reply, expected):
    assert parse_status(reply) == expected


@pytest.mark.parametrize("reply", [
    "no status line at all",
    "STATUS: SOMETHING_ELSE",
    "",
    "   ",
    "STATUS: APPROVED\nbut wait there's more text after",  # not last line
])
def test_unrecognized_returns_ambiguous(reply):
    assert parse_status(reply) == "ambiguous"


def test_blank_lines_between_status_and_content():
    reply = "Critique here.\n\n\n\nSTATUS: CHANGES_REQUESTED\n"
    assert parse_status(reply) == "changes_requested"
