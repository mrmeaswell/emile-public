import json

import validators


# --- lint_language ----------------------------------------------------------

def test_lint_clean_text_passes():
    assert validators.lint_language("Maya checks the NTFS permissions on the shared folder.") == {"pass": True, "hits": []}


def test_lint_three_simplys_reports_three_hits_with_lines():
    # Seed eval #6: a draft containing "simply" three times.
    text = "First, simply open Settings.\nThen click Update.\nSimply restart, and simply wait."
    result = validators.lint_language(text)
    assert result["pass"] is False
    assert [h["line"] for h in result["hits"]] == [1, 3, 3]
    assert all(h["phrase"].lower() == "simply" for h in result["hits"])


def test_lint_catches_every_banned_phrase_in_text_order():
    text = "Obviously this matters.\nAs you know, and as you already know,\nthis is basic."
    hits = validators.lint_language(text)["hits"]
    assert [h["phrase"].lower() for h in hits] == ["obviously", "as you know", "as you already know", "this is basic"]


def test_lint_ignores_substrings():
    assert validators.lint_language("Simplyfing is not a word; simplicity is fine.")["pass"] is True


# --- validate_quiz ----------------------------------------------------------

def test_valid_quiz_passes(valid_quiz):
    result = validators.validate_quiz(json.dumps(valid_quiz))
    assert result["issues"] == []
    assert result["pass"] is True
    assert result["counts"] == validators.TYPES
    assert result["levels"] == {"recall": 10, "application": 16, "analysis": 9}


def test_invalid_json_reports_instead_of_raising():
    result = validators.validate_quiz("{not json")
    assert result["pass"] is False and result["issues"][0].startswith("invalid JSON")


def test_missing_questions_list():
    assert validators.validate_quiz('{"title": "x"}')["pass"] is False


def test_wrong_type_counts(valid_quiz):
    valid_quiz["questions"][0] = valid_quiz["questions"][10]  # one TF becomes MC
    issues = validators.validate_quiz(json.dumps(valid_quiz))["issues"]
    assert "true_false: 6 (target 7)" in issues
    assert "multiple_choice: 13 (target 12)" in issues


def test_difficulty_mix_tolerance(valid_quiz):
    qs = valid_quiz["questions"]
    for q in qs[10:12]:  # 2 application -> recall: still within ±2
        q["level"] = "recall"
    assert validators.validate_quiz(json.dumps(valid_quiz))["pass"] is True
    qs[12]["level"] = "recall"  # 3 off: flagged
    issues = validators.validate_quiz(json.dumps(valid_quiz))["issues"]
    assert any(i.startswith("recall:") for i in issues)
    assert any(i.startswith("application:") for i in issues)


def test_all_or_none_of_the_above(valid_quiz):
    valid_quiz["questions"][8]["options"][3] = "All of the above"
    valid_quiz["questions"][9]["options"][3] = "None of the Above"
    issues = validators.validate_quiz(json.dumps(valid_quiz))["issues"]
    assert "Q9: all/none of the above" in issues and "Q10: all/none of the above" in issues


def test_missing_objective(valid_quiz):
    valid_quiz["questions"][0]["objective"] = "  "
    del valid_quiz["questions"][1]["objective"]
    issues = validators.validate_quiz(json.dumps(valid_quiz))["issues"]
    assert "Q1: no objective mapped" in issues and "Q2: no objective mapped" in issues


def test_double_negative(valid_quiz):
    valid_quiz["questions"][0]["stem"] = "Which setting would Ben not want to leave disabled if he can't reboot?"
    assert "Q1: possible double negative, review" in validators.validate_quiz(json.dumps(valid_quiz))["issues"]


def test_answer_shapes(valid_quiz):
    qs = valid_quiz["questions"]
    qs[7]["answer"] = [0, 1]  # MC with two answers
    qs[19]["answer"] = [0]  # MA with one answer
    qs[25]["answer"] = []  # FIB with no accepted strings
    qs[0]["answer"] = [5]  # TF out of range
    issues = validators.validate_quiz(json.dumps(valid_quiz))["issues"]
    assert "Q8: multiple_choice needs exactly one answer" in issues
    assert "Q20: multiple_answer needs two or more answers" in issues
    assert "Q26: fill_blank needs answer as a list of accepted strings" in issues
    assert "Q1: answer index out of range" in issues


def test_true_false_options_may_be_omitted(valid_quiz):
    del valid_quiz["questions"][0]["options"]
    assert validators.validate_quiz(json.dumps(valid_quiz))["pass"] is True


def test_unknown_type_and_level(valid_quiz):
    valid_quiz["questions"][0]["type"] = "matching"
    valid_quiz["questions"][1]["level"] = "synthesis"
    issues = validators.validate_quiz(json.dumps(valid_quiz))["issues"]
    assert "Q1: unknown type 'matching'" in issues and "Q2: unknown level 'synthesis'" in issues


# --- check_load -------------------------------------------------------------

NET_TERMS = ["VLAN", "trunking", "STP", "LACP", "QinQ", "802.1Q"]


def test_load_flags_overloaded_segment():
    # Seed eval #4: VLANs, trunking, STP, LACP, and QinQ in one segment.
    text = "# Switching\nVLAN, trunking with 802.1Q, STP, LACP, and QinQ.\n# Recap\nVLAN again."
    result = validators.check_load(text, NET_TERMS)
    assert result["pass"] is False
    assert result["segments"][0] == {"heading": "Switching", "count": 6, "terms": NET_TERMS, "over": True}
    assert result["segments"][1]["count"] == 0  # reuse is not new load


def test_load_passes_when_split():
    text = "## VLANs\nVLAN and 802.1Q trunking.\n## Loops\nSTP and LACP.\n## Carriers\nQinQ."
    result = validators.check_load(text, NET_TERMS)
    assert result["pass"] is True
    assert [s["count"] for s in result["segments"]] == [3, 2, 1]


def test_load_counts_intro_and_heading_text():
    result = validators.check_load("VLAN intro.\n# STP basics\nbody", ["VLAN", "STP"])
    assert [(s["heading"], s["count"]) for s in result["segments"]] == [("(intro)", 1), ("STP basics", 1)]


def test_load_matches_whole_terms_only():
    assert validators.check_load("# A\nSTPX is not STP-related? It is.", ["STP"])["segments"][0]["count"] == 1
    assert validators.check_load("# A\nSTPX only.", ["STP"])["segments"][0]["count"] == 0
