"""Document parsers: PDF / DOCX / TXT / MD / CSV / JSON exports.

All parsers return a ParsedDocument preserving filename, source_type and
page/line provenance. Optional deps (pypdf, python-docx) degrade gracefully.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field


@dataclass
class Segment:
    text: str
    page: int = 1
    line_start: int = 1
    line_end: int = 1


@dataclass
class ParsedDocument:
    filename: str
    source_type: str
    segments: list[Segment] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(s.text for s in self.segments)


def _ext(filename: str) -> str:
    name = (filename or "").lower()
    return "." + name.rsplit(".", 1)[-1] if "." in name else ""


def parse_txt(filename: str, data: bytes) -> ParsedDocument:
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines() or [""]
    segs = [
        Segment(text=line, page=1, line_start=i + 1, line_end=i + 1)
        for i, line in enumerate(lines)
        if line.strip()
    ]
    if not segs:
        segs = [Segment(text="", page=1, line_start=1, line_end=1)]
    return ParsedDocument(filename=filename, source_type="txt", segments=segs)


def parse_csv(filename: str, data: bytes) -> ParsedDocument:
    text = data.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    segs: list[Segment] = []
    for i, row in enumerate(reader):
        line = " | ".join(c.strip() for c in row).strip()
        if line:
            segs.append(Segment(text=line, page=1, line_start=i + 1, line_end=i + 1))
    if not segs:
        segs = [Segment(text="", page=1, line_start=1, line_end=1)]
    return ParsedDocument(filename=filename, source_type="csv", segments=segs)


def parse_json(filename: str, data: bytes) -> ParsedDocument:
    """Chat/task exports: list of {role/content|text|message} or generic JSON."""
    raw = json.loads(data.decode("utf-8", errors="replace"))
    segs: list[Segment] = []

    def _one(obj: object, idx: int) -> str:
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            for key in ("content", "text", "message", "body", "title"):
                if isinstance(obj.get(key), str) and obj[key].strip():
                    role = obj.get("role") or obj.get("author") or obj.get("user") or ""
                    prefix = f"[{role}] " if role else ""
                    return prefix + str(obj[key]).strip()
            return json.dumps(obj, ensure_ascii=False)
        return json.dumps(obj, ensure_ascii=False)

    items = raw if isinstance(raw, list) else raw.get("messages", raw.get("tasks", [raw])) if isinstance(raw, dict) else [raw]
    if not isinstance(items, list):
        items = [items]
    for i, item in enumerate(items):
        t = _one(item, i).strip()
        if t:
            segs.append(Segment(text=t, page=1, line_start=i + 1, line_end=i + 1))
    if not segs:
        segs = [Segment(text="", page=1, line_start=1, line_end=1)]
    return ParsedDocument(filename=filename, source_type="json", segments=segs)


def parse_pdf(filename: str, data: bytes) -> ParsedDocument:
    try:
        from pypdf import PdfReader
    except ImportError:
        # Fallback: try raw text extraction hint; else placeholder segment.
        try:
            text = data.decode("utf-8", errors="replace")
            if text.strip() and len(text.strip()) > 20:
                return ParsedDocument(
                    filename=filename, source_type="pdf",
                    segments=[Segment(text=text.strip(), page=1, line_start=1, line_end=1)],
                )
        except Exception:
            pass
        return ParsedDocument(
            filename=filename, source_type="pdf",
            segments=[Segment(text=f"[PDF '{filename}' requires pypdf to parse]", page=1, line_start=1, line_end=1)],
        )
    reader = PdfReader(io.BytesIO(data))
    segs: list[Segment] = []
    for pno, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        for lno, line in enumerate(text.splitlines()):
            if line.strip():
                segs.append(Segment(text=line.strip(), page=pno + 1, line_start=lno + 1, line_end=lno + 1))
    if not segs:
        segs = [Segment(text="", page=1, line_start=1, line_end=1)]
    return ParsedDocument(filename=filename, source_type="pdf", segments=segs)


def parse_docx(filename: str, data: bytes) -> ParsedDocument:
    try:
        import docx
    except ImportError:
        return ParsedDocument(
            filename=filename, source_type="docx",
            segments=[Segment(text=f"[DOCX '{filename}' requires python-docx to parse]", page=1, line_start=1, line_end=1)],
        )
    doc = docx.Document(io.BytesIO(data))
    segs: list[Segment] = []
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            segs.append(Segment(text=para.text.strip(), page=1, line_start=i + 1, line_end=i + 1))
    for tno, table in enumerate(doc.tables):
        for row in table.rows:
            line = " | ".join(c.text.strip() for c in row.cells).strip(" |")
            if line:
                segs.append(Segment(text=line, page=1, line_start=len(segs) + 1, line_end=len(segs) + 1))
    if not segs:
        segs = [Segment(text="", page=1, line_start=1, line_end=1)]
    return ParsedDocument(filename=filename, source_type="docx", segments=segs)


def parse_bytes(filename: str, data: bytes) -> ParsedDocument:
    ext = _ext(filename)
    if ext == ".pdf":
        return parse_pdf(filename, data)
    if ext in {".docx"}:
        return parse_docx(filename, data)
    if ext == ".csv":
        return parse_csv(filename, data)
    if ext == ".json":
        return parse_json(filename, data)
    # .txt, .md, unknown -> plain text
    doc = parse_txt(filename, data)
    doc.source_type = ext.lstrip(".") or "txt"
    if doc.source_type not in {"txt", "md"}:
        doc.source_type = "txt"
    return doc
