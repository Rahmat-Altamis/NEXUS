"""test_01: basic retrieval — authorized user gets an evidence-backed answer."""

import re

from conftest import auth, chat


def test_basic_retrieval_ok(client, tokens):
    body = chat(client, auth(tokens, "siti"), "reset password akun")
    assert body["status"] == "ok"
    assert body["citations"], "expected at least one citation"
    assert "password" in body["answer"].lower()
    assert re.search(r"\[\d+:\d+\]", body["answer"]), "answer must carry [doc:chunk] citations"


def test_basic_retrieval_english(client, tokens):
    body = chat(client, auth(tokens, "siti"), "reset password akun", lang="en")
    assert body["status"] == "ok"
    assert body["answer"].startswith("Based on")


def test_cited_doc_is_readable(client, tokens):
    body = chat(client, auth(tokens, "siti"), "reset password akun")
    doc_id = body["citations"][0]["doc_id"]
    resp = client.get(f"/documents/{doc_id}", headers=auth(tokens, "siti"))
    assert resp.status_code == 200
    assert resp.json()["filename"] == "it-security-policy.md"
