"""test_04: conflict — equal-authority contradictions surface both sides + dates."""

from conftest import auth, chat


def test_unresolved_conflict_shows_both_sides(client, tokens):
    body = chat(client, auth(tokens, "siti"), "Berapa hari cuti tahunan karyawan")
    assert body["status"] == "conflict"
    assert "2025-06-01" in body["answer"]  # v1 effective date
    assert "2026-02-01" in body["answer"]  # v2 effective date
    assert len(body["citations"]) >= 2
    assert any("bertentangan" in w.lower() for w in body["warnings"])


def test_resolved_conflict_prefers_newer_announcement(client, tokens):
    body = chat(client, auth(tokens, "siti"), "tunjangan transport")
    assert body["status"] == "ok"
    assert "750.000" in body["answer"]  # winner: newer HR announcement
    assert any("diselesaikan" in w.lower() or "resolved" in w.lower() for w in body["warnings"])
