"""test_03: revocation — policy change takes effect immediately + history redacts."""

from conftest import auth, chat

QUERY = "pelaporan Zebramango"
DOC_TEXT = ("Prosedur pelaporan Proyek Zebramango: kirim laporan mingguan "
            "kepada manajer melalui kanal bantuan resmi.")


def test_revocation_immediate_and_history_redacted(client, tokens):
    mgr, emp = auth(tokens, "budi"), auth(tokens, "siti")

    # Manager uploads a doc the employee may read (same department).
    resp = client.post(
        "/documents/upload?department=engineering&author=budi",
        files={"file": ("zebramango-probe.txt", DOC_TEXT.encode(), "text/plain")},
        headers=mgr,
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]

    # Readable before revocation.
    before = chat(client, emp, QUERY)
    assert before["status"] == "ok"
    assert any(c["doc_id"] == doc_id for c in before["citations"])

    # Revoke -> immediately refused (fresh policy load, no cache).
    resp = client.put(f"/documents/{doc_id}/policy", json={"status": "revoked"}, headers=mgr)
    assert resp.status_code == 200
    after = chat(client, emp, QUERY)
    assert after["status"] == "refused"
    assert "mingguan" not in after["answer"]

    # History re-checks authz: earlier answer is now redacted.
    resp = client.get("/chat/history?limit=50", headers=emp)
    assert resp.status_code == 200
    items = [i for i in resp.json() if "Zebramango" in i["query"]]
    assert items, "probe query must appear in own history"
    redacted = [i for i in items if i["redacted"]]
    assert redacted, "pre-revocation answer citing the doc must be redacted"
    assert redacted[0]["answer"] == "[redacted: access revoked]"
