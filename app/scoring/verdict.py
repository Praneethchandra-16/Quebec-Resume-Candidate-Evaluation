"""Verdict and feedback.

For a single candidate, a rank of one is useless - the recruiter needs a read.
This produces that read deterministically from the evidence, with no second LLM
call, so the same resume always yields the same verdict.

Wording is deliberately advisory. "Strong match on the evidence" is a claim about
documents. "Hire" is a claim about a person, and this system is not entitled to
make it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from app.schemas.evidence import CandidateReport, EvidenceStrength
from app.schemas.job import JobDescription

SOLID = (
    EvidenceStrength.PROFESSIONAL_EVIDENCE,
    EvidenceStrength.STRONG_PRODUCTION_EVIDENCE,
)


@dataclass
class Verdict:
    label: str
    tone: str  # "success" | "info" | "warning" | "error"
    headline: str
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    thin: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    must_have_hit: int = 0
    must_have_total: int = 0


def _bucket(job: JobDescription, report: CandidateReport) -> Tuple[List, List, List]:
    strong, thin, missing = [], [], []
    for req in job.must_haves:
        match = report.match(req.id)
        if not match or match.strength == EvidenceStrength.NOT_FOUND:
            missing.append(req)
        elif match.strength in SOLID:
            strong.append(req)
        else:
            thin.append(req)
    return strong, thin, missing


def build_verdict(job: JobDescription, report: CandidateReport) -> Verdict:
    strong, thin, missing = _bucket(job, report)
    total = len(job.must_haves) or 1
    hit = len(strong)
    ratio = hit / total
    score = report.score

    # Weighted view: missing a weight-20 requirement is not the same as missing
    # a weight-3 one, so the label uses weight coverage, not a raw count.
    missing_weight = sum(r.weight for r in missing)
    total_weight = job.total_must_have_weight
    critical_gap = missing_weight / total_weight > 0.35

    if score >= 75 and not critical_gap:
        label, tone = "Strong match", "success"
        headline = (
            "Demonstrated experience across most of what this role requires, "
            "with described work rather than skill lists behind it."
        )
    elif score >= 55:
        label, tone = "Worth interviewing", "info"
        headline = (
            "Covers a good share of the requirements. Some areas rest on thin "
            "evidence and are worth probing in a screening call."
        )
    elif score >= 35:
        label, tone = "Partial match", "warning"
        headline = (
            "Real overlap with the role, but several core requirements have no "
            "supporting evidence in the material provided."
        )
    else:
        label, tone = "Weak match on this JD", "error"
        headline = (
            "Little evidence for the core requirements. This may be a strong "
            "candidate for a different opening."
        )

    verdict = Verdict(
        label=label,
        tone=tone,
        headline=headline,
        must_have_hit=hit,
        must_have_total=total,
    )

    verdict.strengths = [
        f"{r.skill} — evidenced in professional work" for r in strong[:6]
    ]
    verdict.thin = [
        f"{r.skill} — appears, but only as a listed skill" for r in thin[:6]
    ]
    verdict.gaps = [f"{r.skill} — no evidence found" for r in missing[:6]]

    for r in thin[:3]:
        verdict.questions.append(
            f"Ask what they actually built with {r.skill}, and at what scale."
        )
    for r in missing[:2]:
        verdict.questions.append(
            f"Confirm whether they have any {r.skill} exposure not captured on the resume."
        )
    if any(f.kind == "low_evidence_density" for f in report.flags):
        verdict.questions.append(
            "The resume lists many technologies with little described work. "
            "A short technical screen would separate breadth from familiarity."
        )
    if any(f.kind == "timeline_impossible" for f in report.flags):
        verdict.questions.append(
            "One or more claimed durations look inconsistent with when the "
            "technology existed. Worth clarifying directly."
        )
    return verdict
