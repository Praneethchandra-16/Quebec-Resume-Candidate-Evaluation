"""End-to-end run: JD + resume files -> ranked, explained reports.

Kept as plain sequential Python rather than LangGraph. The stages are pure
functions with explicit inputs, so swapping in a StateGraph later is mechanical,
and until there is branching or human-in-the-loop to model, a graph would be
ceremony without benefit.

Every stage is wrapped: one broken PDF must not take down a batch of fifty.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from app.agents.github_agent import analyze_github
from app.agents.jd_agent import analyze_jd, analyze_jd_file
from app.agents.matcher_agent import match_candidate
from app.agents.portfolio_agent import analyze_portfolio, handle_linkedin
from app.agents.resume_agent import extract_profile
from app.schemas.candidate import CandidateProfile, LinkKind, ParsedResume
from app.schemas.evidence import CandidateReport, Flag
from app.schemas.job import JobDescription
from app.scoring.score import rank, score_candidate
from app.scoring.verdict import Verdict, build_verdict
from app.tools.pdf_parser import parse_resume
from app.tools.redaction import redact
from app.tools.validator import validate_matches

Progress = Optional[Callable[[str, float], None]]


@dataclass
class CandidateResult:
    """Everything the UI needs about one candidate."""

    report: CandidateReport
    profile: Optional[CandidateProfile] = None
    parsed: Optional[ParsedResume] = None
    display_name: str = ""
    error: Optional[str] = None
    verdict: Optional[Verdict] = None
    github: Optional[object] = None
    portfolio: Optional[object] = None
    linkedin: Optional[object] = None

    def enrichment_notes(self) -> Dict[str, str]:
        out = {}
        for key, ev in (
            ("GitHub", self.github),
            ("Portfolio", self.portfolio),
            ("LinkedIn", self.linkedin),
        ):
            if ev is not None:
                out[key] = ev.summary()
        return out

    @property
    def ok(self) -> bool:
        return self.error is None

    def links(self) -> Dict[str, str]:
        if not self.profile:
            return {}
        out = {}
        for kind in (LinkKind.GITHUB, LinkKind.LINKEDIN, LinkKind.PORTFOLIO):
            url = self.profile.link_of(kind)
            if url:
                out[kind.value] = url
        return out


@dataclass
class RunResult:
    job: Optional[JobDescription] = None
    results: List[CandidateResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ranked(self) -> List[CandidateResult]:
        good = [r for r in self.results if r.ok]
        ordered = rank([r.report for r in good])
        by_id = {r.report.candidate_id: r for r in good}
        return [by_id[rep.candidate_id] for rep in ordered]

    @property
    def failed(self) -> List[CandidateResult]:
        return [r for r in self.results if not r.ok]


def _report(progress: Progress, message: str, pct: float) -> None:
    if progress:
        progress(message, min(max(pct, 0.0), 1.0))


def process_candidate(
    job: JobDescription,
    path: Union[str, Path],
    candidate_id: str,
    enrich: bool = True,
) -> CandidateResult:
    parsed = parse_resume(path, candidate_id)
    if len(parsed.text.strip()) < 200:
        raise ValueError(
            "Almost no text extracted. If this is a scanned or image-based PDF, "
            "it needs OCR before it can be reviewed."
        )

    profile = extract_profile(parsed)
    blinded_text, _ = redact(parsed)

    # Follow the links in the resume. Failures here degrade the review, they do
    # not fail it - a candidate is not penalised for a site being down.
    github_ev = portfolio_ev = None
    linkedin_ev = handle_linkedin(profile.link_of(LinkKind.LINKEDIN))
    if enrich:
        gh_url = profile.link_of(LinkKind.GITHUB)
        if gh_url:
            github_ev = analyze_github(gh_url)
        pf_url = profile.link_of(LinkKind.PORTFOLIO)
        if pf_url:
            portfolio_ev = analyze_portfolio(pf_url)

    github_text = github_ev.as_text() if github_ev else ""
    portfolio_text = portfolio_ev.as_text() if portfolio_ev else ""

    matches = match_candidate(
        job, profile, blinded_text, github_text or None, portfolio_text or None
    )

    sources = {
        "resume": blinded_text,
        "github": github_text,
        "portfolio": portfolio_text,
        "linkedin": "",
    }
    matches, flags = validate_matches(
        matches, sources, profile.total_experience_years
    )

    score, breakdown, notes = score_candidate(
        job, matches, profile.total_experience_years
    )

    report = CandidateReport(
        candidate_id=candidate_id,
        matches=matches,
        breakdown=breakdown,
        score=score,
        flags=flags,
        verify_with_recruiter=notes + [f.detail for f in flags],
    )
    return CandidateResult(
        report=report,
        profile=profile,
        parsed=parsed,
        display_name=parsed.contact.name or candidate_id,
        verdict=build_verdict(job, report),
        github=github_ev,
        portfolio=portfolio_ev,
        linkedin=linkedin_ev,
    )


def run(
    jd_source: Union[str, Path],
    resume_paths: List[Union[str, Path]],
    jd_is_text: bool = False,
    progress: Progress = None,
    enrich: bool = True,
) -> RunResult:
    out = RunResult()

    _report(progress, "Analysing the job description...", 0.05)
    try:
        out.job = analyze_jd(str(jd_source)) if jd_is_text else analyze_jd_file(jd_source)
    except Exception as exc:
        out.errors.append(f"Job description analysis failed: {exc}")
        return out

    total = max(len(resume_paths), 1)
    for i, path in enumerate(resume_paths):
        cid = f"CAND-{i + 1:03d}"
        name = Path(path).name
        _report(progress, f"Reviewing {name} ({i + 1} of {total})...", 0.1 + 0.85 * i / total)
        try:
            out.results.append(process_candidate(out.job, path, cid, enrich=enrich))
        except Exception as exc:
            out.results.append(
                CandidateResult(
                    report=CandidateReport(candidate_id=cid),
                    display_name=name,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            out.errors.append(f"{name}: {exc}")
            traceback.print_exc()

    _report(progress, "Ranking candidates...", 1.0)
    return out
