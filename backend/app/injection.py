"""Prompt-injection detection: flag, log, neutralize. Never execute."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above|system)\s+(instructions?|prompts?)",
    r"reveal\s+(confidential|secret|system|private|hidden)",
    r"exfiltrat|leak\s+(data|secrets?|passwords?)",
    r"system\s+prompt\s+(override|reveal|dump|leak|show)",
    r"you\s+are\s+now\s+(a|an|in)\b.{0,40}(jailbreak|dan|unrestricted|without\s+limits)",
    r"\b(jailbreak|prompt\s*injection|bypass\s+(safety|guardrails?|filters?))\b",
    r"act\s+as\s+(if\s+you\s+(have|are)|a\s+(different|new)\s+(ai|assistant|system))",
    r"do\s+not\s+(follow|obey)\s+(your|system|prior)\b",
    r"override\s+(your|system|all)\s+(instructions?|rules?|policies?)",
    r"execute\s+(this|the\s+following)\s+(command|code|instruction)",
    r"send\s+(all|the)\s+(data|documents?|files?|secrets?)\s+to\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def detect(text: str) -> dict:
    matches = sorted({rx.pattern for rx in _COMPILED if rx.search(text or "")})
    return {"flagged": bool(matches), "matches": matches}


def neutralize(text: str) -> str:
    """Strip matched injection spans, replacing with a marker."""
    cleaned = text or ""
    for rx in _COMPILED:
        cleaned = rx.sub("[blocked-instruction]", cleaned)
    return cleaned


def scan_and_log(db: Session, user: str, text: str, source: str = "query") -> dict:
    """Detect + neutralize; log a SecurityEvent when flagged."""
    from .audit import log_security

    result = detect(text)
    if result["flagged"]:
        log_security(db, user, "prompt_injection_blocked", {
            "source": source,
            "patterns": result["matches"],
            "snippet": (text or "")[:200],
        })
    return {"flagged": result["flagged"], "matches": result["matches"], "cleaned": neutralize(text)}
