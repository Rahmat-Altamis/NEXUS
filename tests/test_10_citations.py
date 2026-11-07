"""test_10: citations — every [doc:chunk] maps to a retrieved, readable passage."""

import re

from conftest import auth, chat

CITE_RE = re.compile(r"\[(\d+):(\d+)\]")


def test_citations_match_answer_and_are_readable(client, tokens):
    body = chat(client, auth(tokens, "siti"), "reset password akun")
    in_answer = {(int(d), int(c)) for d, c in CITE_RE.findall(body["answer"])}
    listed = {(c["doc_id"], c["chunk_idx"]) for c in body["citations"]}
    assert in_answer, "answer must contain citations"
    assert in_answer == listed, "no invented or dropped citations"

    for doc_id, _chunk in listed:
        resp = client.get(f"/documents/{doc_id}?include_text=true", headers=auth(tokens, "siti"))
        assert resp.status_code == 200
        assert resp.json().get("text"), "cited doc must expose passage text"


def test_no_vectors_leaked_in_api(client, tokens):
    body = chat(client, auth(tokens, "siti"), "reset password akun")
    blob = repr(body).lower()
    assert "embedding" not in blob
    assert "vector" not in blob
