"""Evidence validation.

Three deterministic checks between the matcher and the scorer:

  1. Quote verification - every quote must actually exist in the source. This is
     the main anti-hallucination control. An unverified quote is discarded and
     the strength falls back to what the surviving evidence supports.
  2. Timeline sanity - "6 years of LangGraph" is not possible for a library
     released in 2024. Flagged for a human, never silently penalised.
  3. Evidence density - if almost everything is MENTIONED, the resume is a list
     of words rather than a record of work. This is what catches keyword stuffing.

None of this uses an LLM. It has to be reproducible.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from app.schemas.evidence import (
    EvidenceStrength,
    Flag,
    RequirementMatch,
)

# Earliest plausible year a candidate could have used the technology.
TECH_FIRST_AVAILABLE: Dict[str, int] = {
    "langgraph": 2024,
    "langchain": 2022,
    "crewai": 2023,
    "autogen": 2023,
    "mcp": 2024,
    "model context protocol": 2024,
    "llamaindex": 2022,
    "gpt-4": 2023,
    "gpt-5": 2025,
    "claude": 2023,
    "chatgpt": 2022,
    "qdrant": 2021,
    "pinecone": 2021,
    "weaviate": 2019,
    "chroma": 2022,
    "ragas": 2023,
    "langsmith": 2023,
    "langfuse": 2023,
    "fastapi": 2018,
    "pytorch": 2016,
    "kubernetes": 2015,
    "docker": 2013,
    "transformers": 2018,
    "lora": 2021,
    "qlora": 2023,
    "vllm": 2023,
}

CURRENT_YEAR = 2026


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _quote_present(quote: str, haystack: str) -> bool:
    q = _normalise(quote)
    if len(q) < 12:
        return False
    if q in haystack:
        return True
    # Tolerate hyphenation and line-break artefacts from PDF extraction.
    loose = re.sub(r"[^a-z0-9 ]", "", q)
    hay_loose = re.sub(r"[^a-z0-9 ]", "", haystack)
    if loose in hay_loose:
        return True
    # Fall back to token overlap for quotes reflowed across columns.
    tokens = [t for t in loose.split() if len(t) > 3]
    if not tokens:
        return False
    hit = sum(1 for t in tokens if t in hay_loose)
    return hit / len(tokens) >= 0.9


def _supported_strength(match: RequirementMatch) -> EvidenceStrength:
    """The strongest level the *verified* evidence can justify."""
    verified = [e for e in match.evidence if e.verified]
    if not verified:
        # No verified quote: a skills-list mention is still plausible, but any
        # claim above MENTIONED has nothing behind it.
        return (
            EvidenceStrength.MENTIONED
            if match.strength != EvidenceStrength.NOT_FOUND
            else EvidenceStrength.NOT_FOUND
        )
    return match.strength


def validate_matches(
    matches: List[RequirementMatch],
    sources: Dict[str, str],
    total_experience_years: Optional[float] = None,
) -> Tuple[List[RequirementMatch], List[Flag]]:
    """sources maps EvidenceSource value -> raw text of that source."""
    normalised = {k: _normalise(v) for k, v in sources.items()}
    flags: List[Flag] = []
    out: List[RequirementMatch] = []

    for match in matches:
        kept = []
        for item in match.evidence:
            haystack = normalised.get(item.source.value, "")
            item.verified = _quote_present(item.quote, haystack)
            if item.verified:
                kept.append(item)
            else:
                flags.append(
                    Flag(
                        kind="unverified_quote",
                        requirement_id=match.requirement_id,
                        detail=(
                            f"{match.skill}: quoted text was not found in the "
                            f"{item.source.value}. Discarded as unreliable."
                        ),
                    )
                )
        match.evidence = kept

        supported = _supported_strength(match)
        if supported.rank < match.strength.rank:
            flags.append(
                Flag(
                    kind="strength_downgraded",
                    requirement_id=match.requirement_id,
                    detail=(
                        f"{match.skill}: claimed {match.strength.value} but only "
                        f"{supported.value} survives verification."
                    ),
                )
            )
            match.strength = supported

        # Timeline check.
        if match.years_claimed:
            earliest = None
            for tech, year in TECH_FIRST_AVAILABLE.items():
                if tech in match.skill.lower():
                    earliest = year
                    break
            if earliest:
                max_possible = CURRENT_YEAR - earliest
                if match.years_claimed > max_possible + 0.5:
                    flags.append(
                        Flag(
                            kind="timeline_impossible",
                            requirement_id=match.requirement_id,
                            detail=(
                                f"{match.skill}: {match.years_claimed:.0f} years claimed, "
                                f"but the technology has existed for about {max_possible}. "
                                f"Recruiter should verify."
                            ),
                        )
                    )
        if (
            match.years_claimed
            and total_experience_years
            and match.years_claimed > total_experience_years + 0.5
        ):
            flags.append(
                Flag(
                    kind="exceeds_career_length",
                    requirement_id=match.requirement_id,
                    detail=(
                        f"{match.skill}: {match.years_claimed:.0f} years claimed exceeds "
                        f"{total_experience_years:.1f} years total experience."
                    ),
                )
            )

        out.append(match)

    flags.extend(_density_flags(out))
    return out, flags


def _density_flags(matches: List[RequirementMatch]) -> List[Flag]:
    found = [m for m in matches if m.strength != EvidenceStrength.NOT_FOUND]
    if len(found) < 5:
        return []
    mentioned = [m for m in found if m.strength == EvidenceStrength.MENTIONED]
    ratio = len(mentioned) / len(found)
    if ratio >= 0.8:
        return [
            Flag(
                kind="low_evidence_density",
                detail=(
                    f"{len(mentioned)} of {len(found)} matched skills appear only as "
                    f"list entries with no described work. This pattern is typical of "
                    f"keyword-optimised resumes; it may also mean a terse CV from a "
                    f"strong engineer. Worth a screening call before ruling either way."
                ),
            )
        ]
    return []
