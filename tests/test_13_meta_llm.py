"""test_13: Meta Model API provider — request shape, citations, safe fallback.

All HTTP is stubbed; these tests never touch the real API. The dummy key
below is not a credential (see also test_09 secret hygiene).
"""

import pytest

from app import llm as llm_mod

DUMMY_KEY = "test-meta-key-not-a-credential"

PASSAGES = [
    {
        "text": "Karyawan tetap berhak atas cuti tahunan 14 hari.",
        "doc_id": 7,
        "chunk_idx": 0,
        "filename": "hr-leave-policy-v2.md",
        "effective_date": "2026-02-01",
        "authority": "sop",
    }
]


class _StubResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _provider(monkeypatch, **env):
    monkeypatch.setenv("LLM_PROVIDER", "meta")
    monkeypatch.setenv("META_API_KEY", DUMMY_KEY)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return llm_mod.get_provider()


def test_meta_request_shape(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, json=json, headers=headers, timeout=timeout)
        return _StubResp({"choices": [{"message": {"content": "Cuti 14 hari. [7:0]"}}]})

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = _provider(monkeypatch)
    assert isinstance(provider, llm_mod.MetaModelLLM)
    out = provider.generate("berapa cuti?", PASSAGES, lang="id")
    assert captured["url"] == "https://api.meta.ai/v1/chat/completions"
    assert captured["headers"] == {"Authorization": f"Bearer {DUMMY_KEY}"}
    assert captured["json"]["model"] == "muse-spark-1.3-contributor"
    assert captured["json"]["temperature"] == 0
    roles = [m["role"] for m in captured["json"]["messages"]]
    assert roles == ["system", "user"]
    assert "[7:0]" in captured["json"]["messages"][1]["content"]
    assert out["answer"] == "Cuti 14 hari. [7:0]"
    assert out["citations"] == [{"doc_id": 7, "chunk_idx": 0}]


def test_meta_model_override(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        assert json["model"] == "muse-spark-1.1"
        return _StubResp({"choices": [{"message": {"content": "ok [7:0]"}}]})

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = _provider(monkeypatch, META_MODEL="muse-spark-1.1")
    assert provider.generate("q", PASSAGES)["answer"].startswith("ok")


def test_meta_falls_back_on_transport_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    import httpx

    monkeypatch.setattr(httpx, "post", boom)
    out = _provider(monkeypatch).generate("berapa cuti?", PASSAGES, lang="id")
    # MockLLM fallback answers extractively from the same passages.
    assert "[7:0]" in out["answer"]


def test_meta_falls_back_on_empty_content(monkeypatch):
    # Reasoning models can return content=null when the budget runs out.
    def fake_post(*a, **k):
        return _StubResp({"choices": [{"message": {"content": None}}]})

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)
    out = _provider(monkeypatch).generate("berapa cuti?", PASSAGES, lang="id")
    assert "[7:0]" in out["answer"]


def test_meta_disabled_without_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "meta")
    monkeypatch.delenv("META_API_KEY", raising=False)
    assert isinstance(llm_mod.get_provider(), llm_mod.MockLLM)


def test_chat_uses_meta_provider_end_to_end(client, tokens, monkeypatch):
    from conftest import auth

    def fake_post(url, json=None, headers=None, timeout=None):
        assert json["model"] == "muse-spark-1.3-contributor"
        return _StubResp(
            {"choices": [{"message": {"content": "Rp750.000 [4:0], Rp500.000 [3:0], fiktif [99:9]."}}]}
        )

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("LLM_PROVIDER", "meta")
    monkeypatch.setenv("META_API_KEY", DUMMY_KEY)
    resp = client.post(
        "/chat",
        json={"message": "tunjangan transport", "lang": "id"},
        headers=auth(tokens, "siti"),
    )
    assert resp.status_code == 200
    body = resp.json()
    # Agent-level citation check drops the invented [99:9]; survivors must
    # all map to retrieved transport passages.
    assert body["citations"], body
    assert "[99:9]" not in body["answer"]
    for c in body["citations"]:
        assert c["doc_id"] in (3, 4) and c["chunk_idx"] == 0
