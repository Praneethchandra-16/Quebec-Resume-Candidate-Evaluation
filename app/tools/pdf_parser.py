"""Deterministic resume parsing: text, page count, links, basic contact fields.

No LLM here on purpose. This layer must be boring and reproducible - if it is
flaky, every agent downstream inherits the flakiness.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pymupdf  # PyMuPDF

from app.schemas.candidate import ExtractedLink, ParsedResume, RawContact
from app.tools.url_extractor import classify, extract_urls_from_text, normalise

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\d[\d\sxX-]{7,}\d)")


def _annotation_links(doc: "pymupdf.Document") -> List[ExtractedLink]:
    out: List[ExtractedLink] = []
    seen = set()
    for page in doc:
        for link in page.get_links():
            uri = link.get("uri")
            if not uri:
                continue
            url = normalise(uri)
            if url in seen:
                continue
            seen.add(url)
            out.append(
                ExtractedLink(url=url, kind=classify(url), source="annotation")
            )
    return out


def _text_links(text: str, already: set[str]) -> List[ExtractedLink]:
    out: List[ExtractedLink] = []
    for url in extract_urls_from_text(text):
        if url in already:
            continue
        already.add(url)
        out.append(ExtractedLink(url=url, kind=classify(url), source="text"))
    return out


def _contact(text: str) -> RawContact:
    head = "\n".join(text.splitlines()[:12])
    email = EMAIL_RE.search(head)
    phone = PHONE_RE.search(head)
    name = None
    for line in text.splitlines():
        line = line.strip()
        if line:
            name = line
            break
    return RawContact(
        name=name,
        email=email.group(0) if email else None,
        phone=phone.group(0).strip() if phone else None,
    )


def parse_pdf(path: str | Path, candidate_id: str) -> ParsedResume:
    path = Path(path)
    doc = pymupdf.open(path)
    try:
        pages = [page.get_text("text") for page in doc]
        text = "\n".join(pages)
        links = _annotation_links(doc)
        seen = {link.url for link in links}
        links += _text_links(text, seen)
        meta = {k: str(v) for k, v in (doc.metadata or {}).items() if v}
        page_count = doc.page_count
    finally:
        doc.close()

    return ParsedResume(
        candidate_id=candidate_id,
        source_file=str(path),
        text=text,
        page_count=page_count,
        links=links,
        contact=_contact(text),
        meta=meta,
    )


def parse_docx(path: str | Path, candidate_id: str) -> ParsedResume:
    from docx import Document  # imported lazily; python-docx is optional

    path = Path(path)
    document = Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs)

    links: List[ExtractedLink] = []
    seen: set[str] = set()
    for rel in document.part.rels.values():
        if rel.reltype.endswith("/hyperlink"):
            url = normalise(rel.target_ref)
            if url not in seen:
                seen.add(url)
                links.append(
                    ExtractedLink(url=url, kind=classify(url), source="annotation")
                )
    links += _text_links(text, seen)

    return ParsedResume(
        candidate_id=candidate_id,
        source_file=str(path),
        text=text,
        page_count=1,
        links=links,
        contact=_contact(text),
    )


def parse_resume(path: str | Path, candidate_id: str) -> ParsedResume:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path, candidate_id)
    if suffix == ".docx":
        return parse_docx(path, candidate_id)
    raise ValueError(f"Unsupported resume format: {suffix}")
