"""test_02: unauthorized — restricted content is refused generically, no leak."""

from conftest import auth, chat

QUERY = "revenue kuartal"


def test_unauthorized_refused_without_leak(client, tokens):
    body = chat(client, auth(tokens, "siti"), QUERY)
    assert body["status"] == "refused"
    assert body["citations"] == []
    assert "tidak dapat menjawab" in body["answer"].lower()
    assert "1.200.000.000" not in body["answer"]
    assert "Rp" not in body["answer"]


def test_unauthorized_refused_english(client, tokens):
    body = chat(client, auth(tokens, "siti"), QUERY, lang="en")
    assert body["status"] == "refused"
    assert "cannot answer" in body["answer"].lower()


def test_authorized_user_gets_answer(client, tokens):
    body = chat(client, auth(tokens, "dewi"), QUERY)
    assert body["status"] == "ok"
    assert "1.200.000.000" in body["answer"]
    assert body["citations"], "authorized answer must cite sources"


def test_direct_doc_access_denied(client, tokens, seeded_ids):
    doc_id = seeded_ids["finance-quarterly-report.md"]
    resp = client.get(f"/documents/{doc_id}", headers=auth(tokens, "siti"))
    assert resp.status_code == 403
    resp = client.get(f"/documents/{doc_id}", headers=auth(tokens, "dewi"))
    assert resp.status_code == 200
