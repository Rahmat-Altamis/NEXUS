"""test_07: PII — masked by default; unmasked only for privileged role + opt-in."""

from conftest import auth, chat


def test_pii_masked_for_employee(client, tokens):
    body = chat(client, auth(tokens, "siti"), "telepon Andini Pratama")
    assert body["status"] == "ok"
    assert body["masked_pii"] is True
    assert "[PHONE]" in body["answer"]
    assert "0812-3456-7890" not in body["answer"]
    assert "3174000000000001" not in body["answer"]


def test_nik_masked_for_employee(client, tokens):
    body = chat(client, auth(tokens, "siti"), "nik Bambang Sutrisno")
    assert body["status"] == "ok"
    assert body["masked_pii"] is True
    assert "[NIK]" in body["answer"]
    assert "3174000000000002" not in body["answer"]


def test_pii_unmasked_for_hr_with_opt_in(client, tokens):
    body = chat(client, auth(tokens, "hana"), "telepon Andini Pratama", allow_pii=True)
    assert body["status"] == "ok"
    assert body["masked_pii"] is False
    assert "0812-3456-7890" in body["answer"]


def test_pii_still_masked_for_employee_with_opt_in(client, tokens):
    body = chat(client, auth(tokens, "siti"), "telepon Andini Pratama", allow_pii=True)
    assert body["masked_pii"] is True
    assert "0812-3456-7890" not in body["answer"]


def test_email_masked_for_employee(client, tokens):
    body = chat(client, auth(tokens, "siti"), "telepon Citra Ayu Lestari")
    assert "[EMAIL]" in body["answer"] or "[PHONE]" in body["answer"]
    assert "citra.lestari@example.com" not in body["answer"]
