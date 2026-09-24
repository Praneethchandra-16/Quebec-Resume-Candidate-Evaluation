"""Blinding.

Removes identity signals before any qualification analysis. This is structural,
not a polite request in a prompt - the matching model literally never receives
the name.

It is not perfect. Names embedded mid-sentence, gendered pronouns and
university-linked signals can survive. It reduces the surface, and the report
says so rather than claiming the review is bias-free.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from app.schemas.candidate import ParsedResume

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?){2,4}\d{2,4}")
DOB = re.compile(
    r"(?i)\b(date of birth|d\.?o\.?b\.?|born|age)\b\s*[:\-]?\s*[^\n]{0,40}"
)
MARITAL = re.compile(
    r"(?i)\b(marital status|gender|sex|nationality|religion|caste|"
    r"father'?s name|mother'?s name|spouse)\b\s*[:\-]?\s*[^\n]{0,40}"
)
ADDRESS = re.compile(
    r"(?i)\b(address|residence|permanent address)\b\s*[:\-]?\s*[^\n]{0,80}"
)
PRONOUNS = re.compile(r"(?i)\b(he|she|him|her|his|hers)\b")

# Instruction-injection patterns hidden in resume text.
INJECTION = re.compile(
    r"(?i)(ignore (all |the )?(previous|prior|above) instructions?|"
    r"disregard .{0,30}instructions?|you are now|system prompt|"
    r"rate this candidate|rank (this|me) (highly|first|top)|"
    r"as an ai (language )?model)"
)


def redact(parsed: ParsedResume) -> Tuple[str, List[str]]:
    """Return (blinded_text, notes)."""
    text = parsed.text
    notes: List[str] = []

    if INJECTION.search(text):
        notes.append(
            "SECURITY: resume text contains language resembling a prompt "
            "injection attempt. Treated as inert data; flag for recruiter review."
        )

    # Order matters. Emails and phones must go first: replacing the name inside
    # "aarav.menon@example.com" leaves a mangled string the email pattern can no
    # longer match, and the domain survives into the blinded text.
    text = EMAIL.sub("[EMAIL]", text)
    text = PHONE.sub("[PHONE]", text)

    name = (parsed.contact.name or "").strip()
    if name and 1 < len(name) < 60:
        for part in [name] + name.split():
            if len(part) > 2:
                text = re.sub(re.escape(part), "[REDACTED]", text, flags=re.I)
    for pattern, label in (
        (DOB, "[DOB REMOVED]"),
        (MARITAL, "[PERSONAL DETAIL REMOVED]"),
        (ADDRESS, "[ADDRESS REMOVED]"),
    ):
        text, n = pattern.subn(label, text)
        if n:
            notes.append(f"Removed {n} protected-attribute field(s).")

    text = PRONOUNS.sub("they", text)

    # Keep the URLs - they are job-relevant evidence, and the enrichment agents
    # need them. They do leak identity; that is a deliberate, noted trade-off.
    notes.append(
        "Blinded: name, contact details and protected attributes removed. "
        "Profile URLs retained as evidence sources."
    )
    return text, notes


def is_blinded(text: str, name: str) -> bool:
    """Test helper: confirm a name no longer appears."""
    if not name:
        return True
    return not re.search(re.escape(name.split()[0]), text, flags=re.I)
