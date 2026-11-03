"""Your tests go in this file. Two examples to show the fixtures; replace or extend them.

Write tests that would PASS on a correct implementation of the rules in RULES.md.
Some of your tests are expected to FAIL on the copy you were given: each failure
is a finding. Report it in HANDIN.md.
"""
import pytest

from saangai_retrieval import PermissionDenied


def test_public_law_query_returns_only_public_law(make_retriever):
    r = make_retriever()
    results = r.retrieve("u02", None, "lease registration three years")
    assert results, "expected some public-law results"
    assert all(res.matter_id is None for res in results)


def test_unknown_user_is_denied_and_logged(make_retriever, audit_records):
    r = make_retriever()
    with pytest.raises(PermissionDenied):
        r.retrieve("u99", None, "anything")
    assert audit_records()[-1]["decision"] == "deny"
