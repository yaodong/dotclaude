from converge.seed import build_seed_prompt


def test_seed_includes_topic():
    p = build_seed_prompt("auth refactor")
    assert "auth refactor" in p


def test_seed_falls_back_when_topic_blank():
    p = build_seed_prompt("")
    assert "TBD" in p


def test_seed_lists_three_statuses():
    p = build_seed_prompt("any")
    assert "STATUS: APPROVED" in p
    assert "STATUS: CHANGES_REQUESTED" in p
    assert "STATUS: NEEDS_INFO" in p


def test_seed_specifies_finding_format():
    p = build_seed_prompt("any")
    assert "Severity" in p
    assert "Location" in p
    assert "Issue" in p


def test_seed_asks_for_acknowledgement():
    p = build_seed_prompt("any")
    assert "Acknowledged" in p
