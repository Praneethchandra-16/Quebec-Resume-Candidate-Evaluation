"""Deterministic scoring.

No LLM. Same evidence in, same number out, every time.

The score is derived from whatever the JD agent extracted, so changing the job
description changes the scoring basis automatically. Nothing here knows what
"LangGraph" is.

    must-have coverage   70
    nice-to-have         10
    experience fit       15
    external evidence     5

Evidence strength converts to a multiplier on each requirement's weight. A
skills-list mention earns a quarter of the weight; shipped production work earns
all of it. That single table is what separates this from keyword matching.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.config import get_settings
from app.schemas.evidence import (
    EvidenceSource,
    EvidenceStrength,
    RequirementMatch,
    ScoreBreakdown,
)
from app.schemas.job import JobDescription

STRENGTH_MULTIPLIER: Dict[EvidenceStrength, float] = {
    EvidenceStrength.NOT_FOUND: 0.0,
    EvidenceStrength.MENTIONED: 0.25,
    EvidenceStrength.PROJECT_EVIDENCE: 0.60,
    EvidenceStrength.PROFESSIONAL_EVIDENCE: 0.85,
    EvidenceStrength.STRONG_PRODUCTION_EVIDENCE: 1.0,
}


def _coverage(
    matches_by_id: Dict[str, RequirementMatch], requirements
) -> Tuple[float, float]:
    """(earned, possible) weight for a set of requirements."""
    earned = 0.0
    possible = 0.0
    for req in requirements:
        possible += req.weight
        match = matches_by_id.get(req.id)
        if match:
            earned += req.weight * STRENGTH_MULTIPLIER[match.strength]
    return earned, possible


def _experience_points(
    job: JobDescription, years: Optional[float], budget: float
) -> Tuple[float, Optional[str]]:
    required = job.minimum_experience_years
    if not required:
        return budget, None
    if years is None:
        # Unknown is not the same as zero. Award most of it and say so.
        return budget * 0.7, "Total experience could not be determined from the resume."
    ratio = years / required
    if ratio >= 1.0:
        return budget, None
    # Partial credit, floored at 30% so a strong near-miss is not erased.
    points = budget * max(0.3, ratio)
    return (
        points,
        f"{years:.1f} years against a stated minimum of {required:.0f}.",
    )


def _external_points(matches: List[RequirementMatch], budget: float) -> float:
    """Credit for verified evidence found outside the resume."""
    external = {
        e.source
        for m in matches
        for e in m.evidence
        if e.verified and e.source != EvidenceSource.RESUME
    }
    if not external:
        return 0.0
    per_source = budget / 2.0
    return min(budget, len(external) * per_source)


def score_candidate(
    job: JobDescription,
    matches: List[RequirementMatch],
    total_experience_years: Optional[float] = None,
) -> Tuple[float, ScoreBreakdown, List[str]]:
    """Returns (score, breakdown, notes for the recruiter)."""
    s = get_settings()
    by_id = {m.requirement_id: m for m in matches}
    notes: List[str] = []

    must_earned, must_possible = _coverage(by_id, job.must_haves)
    must_points = (must_earned / must_possible * s.weight_must_have) if must_possible else 0.0

    nice_earned, nice_possible = _coverage(by_id, job.nice_to_haves)
    nice_points = (
        (nice_earned / nice_possible * s.weight_nice_to_have) if nice_possible else s.weight_nice_to_have
    )

    exp_points, exp_note = _experience_points(job, total_experience_years, s.weight_experience)
    if exp_note:
        notes.append(exp_note)

    ext_points = _external_points(matches, s.weight_external)

    breakdown = ScoreBreakdown(
        must_have_coverage=round(must_points, 1),
        nice_to_have_coverage=round(nice_points, 1),
        experience_fit=round(exp_points, 1),
        external_evidence=round(ext_points, 1),
    )

    missing = [
        r.skill
        for r in job.must_haves
        if by_id.get(r.id) and by_id[r.id].strength == EvidenceStrength.NOT_FOUND
    ]
    if missing:
        notes.append("No evidence found for: " + ", ".join(missing[:6]) + ".")

    return round(breakdown.total, 1), breakdown, notes


def rank(reports) -> List:
    """Sort candidates by score, then by strongest must-have coverage as the
    tie-break so equal scores are not ordered by filename."""

    def key(report):
        strong = sum(
            1
            for m in report.matches
            if m.strength == EvidenceStrength.STRONG_PRODUCTION_EVIDENCE
        )
        return (report.score, strong)

    return sorted(reports, key=key, reverse=True)
