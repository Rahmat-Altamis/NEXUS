"""test_05: unknown — no evidence yields explicit uncertainty + owner suggestion."""

from conftest import auth, chat


def test_unknown_is_uncertain_id(client, tokens):
    body = chat(client, auth(tokens, "siti"), "koloni Mars terraforming antariksa")
    assert body["status"] == "uncertain"
    assert body["citations"] == []
    assert "tidak menemukan bukti" in body["answer"].lower()
    assert "pemilik dokumen" in body["answer"].lower()


def test_unknown_is_uncertain_en(client, tokens):
    body = chat(client, auth(tokens, "siti"), "koloni Mars terraforming antariksa", lang="en")
    assert body["status"] == "uncertain"
    assert "could not find" in body["answer"].lower()
    assert "document owner" in body["answer"].lower()


def test_fictional_project_is_uncertain_not_misattributed(client, tokens):
    # "project"/"status" overlap real Komodo/Garuda passages, but the named
    # subject (Atlantis) is absent: answering from them would mislead.
    body = chat(client, auth(tokens, "siti"), "Tell me about project Atlantis status", lang="en")
    assert body["status"] == "uncertain"
    assert body["citations"] == []
    assert "komodo" not in body["answer"].lower()
    assert "garuda" not in body["answer"].lower()
