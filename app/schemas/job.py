"""JD-side data contract.

This is the schema the JD Analyzer agent must fill. Everything downstream
(matching, scoring, reporting) reads from it, so changes here ripple - treat it
as the contract, not as a scratchpad.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RequirementKind(str, Enum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"


class Requirement(BaseModel):
    """A single, atomic, checkable requirement.

    'Strong Python and experience with FastAPI or Flask' is NOT atomic - the JD
    agent must split it into two requirements.
    """

    id: str = Field(description="Stable slug, e.g. 'req_langgraph'")
    skill: str = Field(description="Canonical name, e.g. 'LangGraph'")
    kind: RequirementKind
    weight: int = Field(ge=1, le=20, description="Relative importance, 1-20")
    minimum_years: Optional[float] = Field(
        default=None, description="Only when the JD states a number for this skill"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Equivalent surface forms the resume might use",
    )
    rationale: str = Field(
        default="",
        description="Which JD line this came from. Keeps the agent honest.",
    )

    @field_validator("id")
    @classmethod
    def _slug(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_")


class JobDescription(BaseModel):
    role_title: str
    seniority: Optional[str] = None
    minimum_experience_years: Optional[float] = None
    location: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)
    requirements: List[Requirement] = Field(default_factory=list)
    raw_text: str = Field(default="", exclude=True)

    @property
    def must_haves(self) -> List[Requirement]:
        return [r for r in self.requirements if r.kind == RequirementKind.MUST_HAVE]

    @property
    def nice_to_haves(self) -> List[Requirement]:
        return [r for r in self.requirements if r.kind == RequirementKind.NICE_TO_HAVE]

    @property
    def total_must_have_weight(self) -> int:
        return sum(r.weight for r in self.must_haves) or 1
