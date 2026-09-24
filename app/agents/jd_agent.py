"""JD Analyzer.

Takes arbitrary job-description text - a LinkedIn paste, a PDF, a Word doc -
and returns weighted, atomic requirements. Nothing downstream is hardcoded to a
particular role, so swapping the JD swaps the whole scoring basis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from app.llm.client import get_client
from app.schemas.job import JobDescription
from app.tools.ontology import SKILL_GRAPH

SYSTEM = """You analyse job descriptions for a recruiting support tool.

Return weighted, ATOMIC requirements. Rules:

1. Atomic means one checkable thing per requirement. "Strong Python and
   experience with FastAPI or Flask" becomes TWO requirements: Python, and
   Backend API frameworks.
2. kind is must_have only if the JD presents it as required. Anything under
   "preferred", "nice to have", "bonus" or "a plus" is nice_to_have.
3. weight is 1-20 and reflects how central the skill is to THIS role, judged
   from emphasis, repetition and placement - not from your own opinion about
   which technologies matter.
4. aliases must list the surface forms a resume might realistically use. For
   "Agent orchestration" include LangGraph, CrewAI, AutoGen. For "Backend APIs"
   include FastAPI, Flask, Django REST. Be generous; missed aliases become
   false negatives later.
5. rationale quotes or closely paraphrases the JD line the requirement came
   from. If you cannot point at a line, do not invent the requirement.
6. minimum_years only when the JD states a number FOR THAT SKILL. A global
   "5+ years experience" goes in minimum_experience_years, not on a skill.
7. Extract only what is present. Do not add requirements you think the role
   "should" have.

Do not infer requirements about age, gender, nationality, or anything not
job-related, even if the source text mentions them."""

VOCAB_HINT = (
    "Known skill families you may draw aliases from (not exhaustive): "
    + "; ".join(f"{k}: {', '.join(v[:6])}" for k, v in SKILL_GRAPH.items())
)


def analyze_jd(text: str) -> JobDescription:
    """Structured requirements from raw JD text."""
    if not text or len(text.strip()) < 40:
        raise ValueError("Job description text is too short to analyse")

    client = get_client()
    user = f"{VOCAB_HINT}\n\nJD_TEXT:\n{text.strip()}"
    job = client.structured(JobDescription, system=SYSTEM, user=user)
    job.raw_text = text

    # Guard against an empty or degenerate extraction.
    if not job.must_haves:
        raise ValueError(
            "No must-have requirements were extracted. The JD text may be "
            "truncated, or it may be a company blurb rather than a role spec."
        )
    return job


def analyze_jd_file(path: Union[str, Path]) -> JobDescription:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from app.tools.pdf_parser import parse_pdf

        return analyze_jd(parse_pdf(path, "JD").text)
    if suffix == ".docx":
        from app.tools.pdf_parser import parse_docx

        return analyze_jd(parse_docx(path, "JD").text)
    return analyze_jd(path.read_text(encoding="utf-8"))
