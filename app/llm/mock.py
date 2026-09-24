"""Offline provider.

Implements the same `structured()` contract using regex and the skill ontology
instead of a model. It exists for three reasons:

  1. The Streamlit app runs end-to-end with no API key and no spend.
  2. Tests can exercise the full pipeline deterministically in CI.
  3. It is the baseline. If the LLM pipeline cannot beat crude keyword matching
     on the labelled dataset, the LLM is not earning its cost - and you now have
     the number to prove it either way.

It is deliberately not clever. Do not ship it as the product.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Type

from pydantic import BaseModel

from app.llm.client import BaseClient
from app.tools.ontology import (
    IMPACT_MARKERS,
    PRODUCTION_MARKERS,
    SKILL_GRAPH,
    WEAK_MARKERS,
    aliases_for,
)

SECTION = re.compile(
    r"^\s*(summary|profile|skills?|technical skills|professional experience|"
    r"work experience|experience|projects?|education|certifications?)\s*:?\s*$",
    re.I | re.M,
)


def _payload(user: str, marker: str) -> str:
    """Agents delimit their inputs; the mock reads them back out."""
    if marker not in user:
        return user
    tail = user.split(marker, 1)[1]
    for other in ("JD_TEXT:", "CANDIDATE_TEXT:", "REQUIREMENTS_JSON:"):
        if other != marker and other in tail:
            tail = tail.split(other, 1)[0]
    return tail.strip()


# --------------------------------------------------------------- JD extraction

def _requirement_lines(text: str) -> List[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip(" -*\u2022\t")
        if 4 < len(line) < 200 and not SECTION.match(raw):
            lines.append(line)
    return lines


STOPWORDS = {
    "and", "or", "the", "with", "for", "you", "your", "our", "will", "have",
    "years", "experience", "strong", "using", "must", "should", "able", "work",
    "working", "including", "preferred", "requirements", "responsibilities",
    "plus", "bonus", "nice", "good", "excellent", "understanding", "knowledge",
    "ability", "skills", "this", "that", "from", "into", "across", "such",
}


def _keywords(line: str) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z+#.\-]{2,}", line.lower())
    return [w for w in words if w not in STOPWORDS][:6]


# Section headings that job boards use. These are structure, not requirements.
HEADING_PHRASES = {
    "about the role", "about this role", "about the job", "about us",
    "about the team", "about the company", "what you'll do", "what you will do",
    "what you'll bring", "what you will bring", "who you are", "the role",
    "the opportunity", "responsibilities", "key responsibilities",
    "job responsibilities", "duties", "requirements", "minimum qualifications",
    "basic qualifications", "preferred qualifications", "qualifications",
    "skills", "required skills", "technical skills", "what we offer",
    "benefits", "compensation", "perks", "why join us", "equal opportunity",
    "eeo statement", "diversity", "how to apply", "our stack", "day to day",
    "day-to-day", "nice to have", "nice-to-have", "good to have", "preferred",
    "desired", "must have", "must-have", "your impact", "your profile",
    "cross-functional collaboration", "collaboration", "location", "salary",
}

# Verbs and connectors that signal an actual requirement rather than a label.
REQUIREMENT_SIGNALS = re.compile(
    r"(?i)\b(experience|years|yrs|proficien|familiar|knowledge|ability|able|"
    r"strong|demonstrat|degree|certif|bachelor|master|understanding|hands-on|"
    r"expertise|skilled|working with|build|built|design|develop|deploy|manage|"
    r"maintain|write|writing|using|with|in|of|and|or)\b"
)


def _is_heading(line: str) -> bool:
    """A heading labels a section; a requirement states something checkable."""
    stripped = line.strip().rstrip(":").strip()
    low = stripped.lower()

    if low in HEADING_PHRASES:
        return True
    # "About The Role" / "What You'll Do" style: short, no sentence punctuation,
    # and no requirement language anywhere in it.
    words = stripped.split()
    if len(words) <= 6 and not stripped.endswith((".", ",", ";")):
        if not REQUIREMENT_SIGNALS.search(stripped):
            return True
        # Title Case with every word capitalised is almost always a heading.
        alpha = [w for w in words if w[:1].isalpha()]
        if len(alpha) >= 2 and all(w[:1].isupper() for w in alpha) and not any(
            ch.isdigit() for ch in stripped
        ):
            return True
    if line.strip().endswith(":") and len(words) <= 8:
        return True
    return False


def _bullet_lines(text: str) -> List[str]:
    """Requirement-ish lines only.

    Three filters, in order: drop the job title (first content line), drop
    section headings, and prefer bullets when the posting has them. LinkedIn
    postings in particular are mostly headings and prose, which is how
    "About The Role" ends up scored as a skill if you skip this.
    """
    raw = text.splitlines()
    first_content = next((i for i, l in enumerate(raw) if l.strip()), 0)

    bullets, plain = [], []
    for i, line in enumerate(raw):
        if i <= first_content:
            continue
        stripped = line.strip()
        if not stripped or SECTION.match(line):
            continue
        is_bullet = bool(re.match(r"^\s*[-*\u2022\u25cf\u25aa]", line))
        cleaned = stripped.lstrip("-*\u2022\u25cf\u25aa ").strip()
        if len(cleaned) < 10 or _is_heading(cleaned):
            continue
        (bullets if is_bullet else plain).append(cleaned)

    chosen = bullets if len(bullets) >= 3 else bullets + plain
    # De-duplicate while preserving order.
    seen, out = set(), []
    for c in chosen:
        key = c.lower()[:60]
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _mock_job(text: str) -> Dict[str, Any]:
    """Line-driven, so it works for any job family. The ontology is used only to
    widen aliases on lines that happen to mention known technologies - it never
    decides what the requirements are."""
    lowered = text.lower()

    preferred_at = len(text)
    for kw in ("preferred", "nice to have", "nice-to-have", "bonus", "good to have",
               "desirable", "a plus"):
        idx = lowered.find(kw)
        if idx != -1:
            preferred_at = min(preferred_at, idx)

    requirements: List[Dict[str, Any]] = []
    seen = set()
    for line in _bullet_lines(text):
        kws = _keywords(line)
        if len(kws) < 1:
            continue
        key = re.sub(r"[^a-z0-9]+", "_", kws[0])[:30]
        if key in seen:
            continue
        seen.add(key)

        aliases = list(kws)
        for canonical, forms in SKILL_GRAPH.items():
            if any(f in line.lower() for f in forms):
                aliases.extend(forms[:6])

        pos = lowered.find(line.lower()[:40])
        kind = "nice_to_have" if 0 <= preferred_at <= pos else "must_have"
        requirements.append(
            {
                "id": f"req_{key}",
                "skill": line[:70].rstrip(".,;"),
                "kind": kind,
                "weight": 10 if kind == "must_have" else 4,
                "minimum_years": None,
                "aliases": sorted(set(a.lower() for a in aliases))[:20],
                "rationale": line[:160],
            }
        )
        if len(requirements) >= 22:
            break

    years = None
    m = re.search(r"(\d+)\s*\+?\s*(?:years|yrs)", lowered)
    if m:
        years = float(m.group(1))

    title = "Role"
    for line in text.splitlines():
        stripped = line.strip("# ").strip()
        if stripped:
            title = stripped[:80]
            break

    return {
        "role_title": title,
        "seniority": "senior" if "senior" in lowered else None,
        "minimum_experience_years": years,
        "location": None,
        "responsibilities": _bullet_lines(text)[:8],
        "requirements": requirements,
    }


# ----------------------------------------------------------- resume extraction

def _mock_profile(text: str) -> Dict[str, Any]:
    lowered = text.lower()

    skills: List[str] = []
    for forms in SKILL_GRAPH.values():
        for f in forms:
            if f in lowered and len(f) > 2:
                skills.append(f)

    years = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)", lowered)
    if m:
        years = float(m.group(1))

    experience = []
    job_line = re.compile(r"^(.{3,60}?)\s+-\s+(.{2,60}?)\s*\((.{4,40})\)\s*$", re.M)
    for title, company, dates in job_line.findall(text):
        experience.append(
            {
                "title": title.strip(),
                "company": company.strip(),
                "start_date": None,
                "end_date": None,
                "duration_years": None,
                "technologies": [],
                "responsibilities": [],
            }
        )

    return {
        "candidate_id": "CAND-MOCK",
        "source_file": "",
        "total_experience_years": years,
        "current_title": experience[0]["title"] if experience else None,
        "skills": sorted(set(skills))[:60],
        "work_experience": experience,
        "projects": [],
        "education": [],
        "certifications": [],
        "links": [],
        "parse_warnings": ["extracted by the offline heuristic provider"],
    }


# -------------------------------------------------------------------- matching

def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n", text)
    return [p.strip() for p in parts if len(p.strip()) > 15]


def _skills_block(text: str) -> str:
    m = re.search(r"SKILLS(.{0,1200}?)(?:PROFESSIONAL|WORK|EXPERIENCE|PROJECTS|EDUCATION)",
                  text, re.S | re.I)
    return m.group(1).lower() if m else ""


def _strength(sentence: str) -> str:
    s = sentence.lower()
    if any(w in s for w in WEAK_MARKERS):
        return "MENTIONED"
    has_impact = any(w in s for w in IMPACT_MARKERS)
    has_prod = any(w in s for w in PRODUCTION_MARKERS) or re.search(r"\d[\d,.]*\s*[kmb%]", s)
    if has_impact and has_prod:
        return "STRONG_PRODUCTION_EVIDENCE"
    if has_impact:
        return "PROFESSIONAL_EVIDENCE"
    return "MENTIONED"


def _mock_matches(user: str) -> Dict[str, Any]:
    reqs = json.loads(_payload(user, "REQUIREMENTS_JSON:"))
    text = _payload(user, "CANDIDATE_TEXT:")
    skills_block = _skills_block(text)
    sentences = _sentences(text)

    matches = []
    for req in reqs:
        terms = set(a.lower() for a in req.get("aliases", []))
        terms.update(aliases_for(req["skill"]))
        terms = {t for t in terms if len(t) > 2}

        best_strength = "NOT_FOUND"
        evidence = []
        for sent in sentences:
            low = sent.lower()
            if not any(t in low for t in terms):
                continue
            strength = _strength(sent)
            if _rank(strength) > _rank(best_strength):
                best_strength = strength
            if len(evidence) < 2:
                evidence.append(
                    {
                        "source": "resume",
                        "quote": sent[:240],
                        "context": "",
                        "verified": False,
                    }
                )

        if best_strength == "NOT_FOUND" and any(t in skills_block for t in terms):
            best_strength = "MENTIONED"

        matches.append(
            {
                "requirement_id": req["id"],
                "skill": req["skill"],
                "strength": best_strength,
                "evidence": evidence,
                "years_claimed": None,
                "reasoning": "offline heuristic: alias hit + impact/production markers",
            }
        )
    return {"matches": matches}


def _rank(s: str) -> int:
    return {
        "NOT_FOUND": 0,
        "MENTIONED": 1,
        "PROJECT_EVIDENCE": 2,
        "PROFESSIONAL_EVIDENCE": 3,
        "STRONG_PRODUCTION_EVIDENCE": 4,
    }[s]


class MockClient(BaseClient):
    def _call(self, model: Type[BaseModel], system: str, user: str) -> Dict[str, Any]:
        name = model.__name__
        if name == "JobDescription":
            return _mock_job(_payload(user, "JD_TEXT:"))
        if name == "CandidateProfile":
            return _mock_profile(_payload(user, "CANDIDATE_TEXT:"))
        if name == "MatchSet":
            return _mock_matches(user)
        raise NotImplementedError(f"mock provider has no handler for {name}")
