"""test_11: multilingual retrieval — EN queries find ID evidence and vice versa.

The synthetic corpus is largely Indonesian; the hashed-BoW embedding is
monolingual, so without query expansion an English question over Indonesian
documents scores ~0.0 and yields "uncertain" despite accessible evidence.
"""

from conftest import auth, chat


def test_english_query_finds_indonesian_leave_policy(client, tokens):
    body = chat(client, auth(tokens, "siti"), "What is the annual leave policy?", lang="en")
    assert body["status"] in ("ok", "conflict"), body
    assert body["citations"], f"expected citations, got: {body}"
    answer = body["answer"].lower()
    assert ("cuti" in answer) or ("leave" in answer), body


def test_indonesian_query_finds_leave_evidence(client, tokens):
    body = chat(client, auth(tokens, "siti"), "Berapa hari cuti tahunan karyawan?", lang="id")
    assert body["status"] in ("ok", "conflict"), body
    assert body["citations"], f"expected citations, got: {body}"


def test_english_query_finds_transport_allowance(client, tokens):
    body = chat(client, auth(tokens, "siti"), "What is the monthly transport allowance?", lang="en")
    assert body["status"] in ("ok", "conflict"), body
    assert body["citations"], f"expected citations, got: {body}"
