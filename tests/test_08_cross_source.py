"""test_08: cross-source — SOP + chat + tasks combine into one cited answer."""

from conftest import auth, chat


def test_cross_source_combines_types(client, tokens):
    body = chat(client, auth(tokens, "siti"), "milestone Garuda")
    assert body["status"] == "ok"
    assert len(body["citations"]) >= 2

    source_types = set()
    for cite in body["citations"]:
        resp = client.get(f"/documents/{cite['doc_id']}", headers=auth(tokens, "siti"))
        assert resp.status_code == 200
        source_types.add(resp.json()["source_type"])
    assert len(source_types) >= 2, f"expected >=2 source types, got {source_types}"
    assert "garuda" in body["answer"].lower()
