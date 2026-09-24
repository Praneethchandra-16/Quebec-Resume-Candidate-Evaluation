"""Evidence + result contracts.

The central idea of the whole system lives here: a requirement is not matched by
a keyword, it is matched by *evidence of a given strength, from a given source*.
The LLM produces this. Python turns it into a number.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceStrength(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    MENTIONED = "MENTIONED"                       # skills list only
    PROJECT_EVIDENCE = "PROJECT_EVIDENCE"         # personal/side project
    PROFESSIONAL_EVIDENCE = "PROFESSIONAL_EVIDENCE"   # used at work
    STRONG_PRODUCTION_EVIDENCE = "STRONG_PRODUCTION_EVIDENCE"  # shipped, scaled, owned

    @property
    def rank(self) -> int:
        return {
            "NOT_FOUND": 0,
            "MENTIONED": 1,
            "PROJECT_EVIDENCE": 2,
            "PROFESSIONAL_EVIDENCE": 3,
            "STRONG_PRODUCTION_EVIDENCE": 4,
        }[self.value]


class EvidenceSource(str, Enum):
    RESUME = "resume"
    GITHUB = "github"
    PORTFOLIO = "portfolio"
    LINKEDIN = "linkedin"


class EvidenceItem(BaseModel):
    source: EvidenceSource
    quote: str = Field(
        description="Verbatim span from the source. Must appear in the source text."
    )
    context: str = Field(
        default="", description="e.g. 'AI Engineer @ Zenlytix' or repo name"
    )
    verified: bool = Field(
        default=False,
        description="Set by the validator once the quote is confirmed present.",
    )


class RequirementMatch(BaseModel):
    requirement_id: str
    skill: str
    strength: EvidenceStrength
    evidence: List[EvidenceItem] = Field(default_factory=list)
    years_claimed: Optional[float] = None
    reasoning: str = Field(default="", max_length=600)


class Flag(BaseModel):
    kind: str = Field(description="e.g. 'unverified_quote', 'timeline_impossible'")
    detail: str
    requirement_id: Optional[str] = None


class ScoreBreakdown(BaseModel):
    """Deliberately generic. Categories cannot be role-specific, because the
    requirements come from whatever JD was supplied."""

    must_have_coverage: float = 0
    nice_to_have_coverage: float = 0
    experience_fit: float = 0
    external_evidence: float = 0

    @property
    def total(self) -> float:
        return round(
            self.must_have_coverage
            + self.nice_to_have_coverage
            + self.experience_fit
            + self.external_evidence,
            1,
        )

    def as_rows(self) -> List[tuple]:
        return [
            ("Must-have coverage", self.must_have_coverage),
            ("Nice-to-have coverage", self.nice_to_have_coverage),
            ("Experience fit", self.experience_fit),
            ("External evidence", self.external_evidence),
        ]


class CandidateReport(BaseModel):
    candidate_id: str
    matches: List[RequirementMatch] = Field(default_factory=list)
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    score: float = 0
    flags: List[Flag] = Field(default_factory=list)
    summary: str = ""
    verify_with_recruiter: List[str] = Field(default_factory=list)

    def match(self, requirement_id: str) -> Optional[RequirementMatch]:
        return next(
            (m for m in self.matches if m.requirement_id == requirement_id), None
        )
