"""Candidate-side data contract.

Note the split between `RawContact` and `CandidateProfile`. Identity lives in
RawContact and is deliberately kept *out* of anything the matching model sees;
CandidateProfile is the blinded view (see app/tools/redaction.py in step 3).
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class LinkKind(str, Enum):
    GITHUB = "github"
    LINKEDIN = "linkedin"
    PORTFOLIO = "portfolio"
    OTHER = "other"


class ExtractedLink(BaseModel):
    url: str
    kind: LinkKind
    source: str = Field(description="'annotation' or 'text'")


class RawContact(BaseModel):
    """Identity fields. Never passed to the matching / scoring prompts."""

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None


class Experience(BaseModel):
    title: str
    company: str
    start_date: Optional[str] = Field(default=None, description="YYYY-MM if known")
    end_date: Optional[str] = Field(
        default=None, description="YYYY-MM, or 'present'"
    )
    duration_years: Optional[float] = None
    technologies: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class Education(BaseModel):
    degree: str
    institution: Optional[str] = None
    year: Optional[int] = None


class CandidateProfile(BaseModel):
    """Blinded, structured view of one resume."""

    candidate_id: str = Field(description="e.g. CAND-001. Never the real name.")
    source_file: str = ""

    total_experience_years: Optional[float] = None
    current_title: Optional[str] = None

    skills: List[str] = Field(default_factory=list)
    work_experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

    links: List[ExtractedLink] = Field(default_factory=list)

    parse_warnings: List[str] = Field(default_factory=list)

    def link_of(self, kind: LinkKind) -> Optional[str]:
        for link in self.links:
            if link.kind == kind:
                return link.url
        return None


class ParsedResume(BaseModel):
    """What the parsing stage hands to the extraction agent."""

    candidate_id: str
    source_file: str
    text: str
    page_count: int
    links: List[ExtractedLink] = Field(default_factory=list)
    contact: RawContact = Field(default_factory=RawContact)
    meta: Dict[str, str] = Field(default_factory=dict)
