"""Quebec Candidate Resume Evaluation — recruiter dashboard.

    streamlit run frontend/streamlit_app.py

One resume gives a verdict with feedback. Several give a ranking. Same engine.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_cloud_secrets() -> None:
    """Streamlit Community Cloud supplies secrets through st.secrets, not the
    environment. Mirror them into os.environ so app.config behaves identically
    whether the app is running on a laptop with a .env file or hosted."""
    keys = (
        "LLM_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL",
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "GITHUB_TOKEN",
    )
    try:
        available = st.secrets
    except Exception:
        return  # no secrets.toml locally; .env handles it
    for key in keys:
        try:
            if key in available and not os.environ.get(key):
                os.environ[key] = str(available[key])
        except Exception:
            continue


_load_cloud_secrets()

from app.config import override  # noqa: E402
from app.pipeline import run  # noqa: E402
from app.reporting.export import (  # noqa: E402
    RANKING_COLUMNS,
    REQUIREMENT_COLUMNS,
    build_ranking_rows,
    build_requirement_rows,
    to_csv,
    to_excel,
)
from app.schemas.evidence import EvidenceStrength  # noqa: E402

st.set_page_config(
    page_title="Quebec Candidate Resume Evaluation", page_icon="◆", layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1180px;}
h1, h2, h3 {letter-spacing: -0.02em;}

.tm-hero {
  background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8a 100%);
  padding: 1.6rem 1.9rem; border-radius: 14px; color: #fff; margin-bottom: 1.4rem;
}
.tm-hero h1 {margin: 0; font-size: 1.75rem; color: #fff;}
.tm-hero p {margin: .4rem 0 0; opacity: .82; font-size: .93rem;}

.tm-card {
  border: 1px solid rgba(140,140,160,.22); border-radius: 12px;
  padding: 1rem 1.25rem; margin-bottom: .3rem; background: rgba(140,140,160,.045);
}
.tm-row {display: flex; align-items: center; gap: 1rem;}
.tm-rank {font-size: 1.05rem; font-weight: 700; opacity: .45; min-width: 2.4rem;}
.tm-name {font-size: 1.14rem; font-weight: 650; flex: 1;}
.tm-score {font-size: 1.7rem; font-weight: 750; line-height: 1;}
.tm-score small {font-size: .7rem; font-weight: 500; opacity: .55;}

.tm-pill {
  display: inline-block; padding: .16rem .66rem; border-radius: 999px;
  font-size: .73rem; font-weight: 640;
}
.p-success {background: rgba(28,160,90,.16); color: #1ca05a;}
.p-info    {background: rgba(45,110,200,.16); color: #3d7fd6;}
.p-warning {background: rgba(212,145,20,.17); color: #d49114;}
.p-error   {background: rgba(200,70,70,.15); color: #cc5555;}

.tm-bar {height: 6px; border-radius: 4px; background: rgba(140,140,160,.2); margin-top:.35rem;}
.tm-bar > div {height: 100%; border-radius: 4px;}

.tm-ev {
  border-left: 3px solid rgba(140,140,160,.4); padding: .1rem 0 .1rem .75rem;
  margin: .25rem 0 .5rem; font-size: .83rem; opacity: .8; font-style: italic;
}
.tm-req {font-size: .9rem; margin: .4rem 0 0;}
.tm-meta {font-size: .78rem; opacity: .62;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

STRENGTH = {
    EvidenceStrength.STRONG_PRODUCTION_EVIDENCE: ("●", "#1ca05a", "Shipped in production"),
    EvidenceStrength.PROFESSIONAL_EVIDENCE: ("●", "#3d9a5f", "Used professionally"),
    EvidenceStrength.PROJECT_EVIDENCE: ("◐", "#d49114", "Project work"),
    EvidenceStrength.MENTIONED: ("○", "#c48a30", "Listed only, no described work"),
    EvidenceStrength.NOT_FOUND: ("·", "#8a8a95", "No evidence found"),
}


def score_colour(score: float) -> str:
    if score >= 75:
        return "#1ca05a"
    if score >= 55:
        return "#3d7fd6"
    if score >= 35:
        return "#d49114"
    return "#cc5555"


def _save_temp(uploaded) -> Path:
    tmp = Path(tempfile.gettempdir()) / "quebec-candidate-resume-evaluation"
    tmp.mkdir(exist_ok=True)
    path = tmp / uploaded.name
    path.write_bytes(uploaded.getbuffer())
    return path


# ------------------------------------------------------------------ sidebar

def sidebar():
    st.sidebar.markdown("### Engine")
    provider = st.sidebar.selectbox(
        "Provider", ["mock", "openai", "anthropic"],
        help="'mock' is an offline keyword baseline. No key, no cost, no nuance.",
    )
    model = ""
    if provider == "openai":
        model = st.sidebar.text_input("Model", value="gpt-4o-mini")
    elif provider == "anthropic":
        model = st.sidebar.text_input("Model", value="claude-sonnet-4-5")

    settings = override(provider=provider, model=model or None)
    if not settings.is_configured():
        key = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        st.sidebar.error(f"{key} missing from .env")
    elif provider == "mock":
        st.sidebar.warning(
            "Offline baseline. It cannot tell a listed skill from a shipped one — "
            "switch to a real provider for that."
        )
    else:
        st.sidebar.success(settings.model_name())

    st.sidebar.markdown("### Options")
    enrich = st.sidebar.checkbox(
        "Follow links in resumes", value=True,
        help="Reads public GitHub repos and portfolio sites as extra evidence. "
             "LinkedIn is never fetched — their terms prohibit it.",
    )
    top_n = st.sidebar.slider("Show top", 3, 50, 10)

    st.sidebar.divider()
    st.sidebar.caption(
        "Ranks documented evidence against a job description. It does not decide "
        "who to hire, and every judgement shows the text it came from."
    )
    return enrich, top_n


# ------------------------------------------------------------------- inputs

def inputs():
    st.markdown(
        '<div class="tm-hero"><h1>◆ Quebec Candidate Resume Evaluation</h1>'
        "<p>Paste a job description, drop in resumes. Every score traces back to "
        "a line someone actually wrote.</p></div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 1])

    with left:
        st.markdown("#### Job description")
        jd_text = st.text_area(
            "jd", height=280, label_visibility="collapsed",
            placeholder=(
                "Paste any job posting here — AI Engineer, QA Analyst, Business "
                "Analyst, Data Architect, Support Engineer, anything.\n\n"
                "Include the requirements section. The more complete the posting, "
                "the better the requirement weights."
            ),
        )
        jd_file = st.file_uploader("or upload a JD file", type=["pdf", "docx", "txt", "md"])
        use_sample_jd = st.checkbox("Use the bundled sample JD", value=False)

    with right:
        st.markdown("#### Resumes")
        ups = st.file_uploader(
            "Upload one or many", type=["pdf", "docx"],
            accept_multiple_files=True, label_visibility="collapsed",
        )
        st.caption(
            "One resume gives a verdict with feedback. Several give a ranking.\n\n"
            "Hyperlinks inside the PDF are read even when the visible text is "
            "just \u201cLinkedIn\u201d or \u201cmy portfolio\u201d."
        )
        use_sample_cvs = st.checkbox("Use the 8 bundled sample resumes", value=False)

    jd_source, jd_is_text = None, False
    if jd_text and len(jd_text.strip()) >= 40:
        jd_source, jd_is_text = jd_text, True
    elif jd_file:
        jd_source = str(_save_temp(jd_file))
    elif use_sample_jd:
        sample = ROOT / "data" / "jd" / "senior_ai_engineer.md"
        if sample.exists():
            jd_source = str(sample)

    paths = [str(_save_temp(u)) for u in ups] if ups else []
    if not paths and use_sample_cvs:
        paths = [str(p) for p in sorted((ROOT / "data" / "resumes").glob("*.pdf"))]

    return jd_source, jd_is_text, paths


# ----------------------------------------------------------------- rendering

def render_requirements(job):
    with st.expander(f"What the system read from this JD — {job.role_title}"):
        if job.minimum_experience_years:
            st.markdown(f"**Minimum experience:** {job.minimum_experience_years:.0f} years")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Required**")
            for r in job.must_haves:
                st.markdown(
                    f'<div class="tm-req">{r.skill} '
                    f'<span class="tm-meta">weight {r.weight}</span></div>',
                    unsafe_allow_html=True,
                )
        with c2:
            st.markdown("**Preferred**")
            for r in job.nice_to_haves:
                st.markdown(
                    f'<div class="tm-req">{r.skill} '
                    f'<span class="tm-meta">weight {r.weight}</span></div>',
                    unsafe_allow_html=True,
                )
        st.caption(
            "These weights are extracted from the posting and drive the entire "
            "score. Nothing here is hardcoded to any job family."
        )


def render_verdict(result):
    v = result.verdict
    if not v:
        return
    st.markdown(f'<span class="tm-pill p-{v.tone}">{v.label}</span>', unsafe_allow_html=True)
    st.markdown(f"**{v.headline}**")
    st.caption(f"Evidenced {v.must_have_hit} of {v.must_have_total} required areas.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Backed by real work**")
        for s in v.strengths or ["—"]:
            st.markdown(f"- {s}")
    with c2:
        st.markdown("**Thin evidence**")
        for s in v.thin or ["—"]:
            st.markdown(f"- {s}")
    with c3:
        st.markdown("**Not found**")
        for s in v.gaps or ["—"]:
            st.markdown(f"- {s}")

    if v.questions:
        st.markdown("**Suggested screening questions**")
        for q in v.questions:
            st.markdown(f"- {q}")


def render_evidence(result, job):
    report = result.report
    for req in job.must_haves + job.nice_to_haves:
        match = report.match(req.id)
        if not match:
            continue
        icon, colour, label = STRENGTH[match.strength]
        tag = "" if req.kind.value == "must_have" else " · preferred"
        st.markdown(
            f'<div class="tm-req"><span style="color:{colour}">{icon}</span> '
            f"<b>{req.skill}</b>{tag} — "
            f'<span class="tm-meta">{label}</span></div>',
            unsafe_allow_html=True,
        )
        for ev in match.evidence[:2]:
            src = "" if ev.source.value == "resume" else f" [{ev.source.value}]"
            st.markdown(
                f'<div class="tm-ev">\u201c{ev.quote}\u201d{src}</div>',
                unsafe_allow_html=True,
            )


def render_side_panel(result):
    report = result.report
    st.markdown("**Score breakdown**")
    for label, value in report.breakdown.as_rows():
        st.markdown(
            f'<div class="tm-meta">{label} · {value:.1f}</div>'
            f'<div class="tm-bar"><div style="width:{min(value * 1.4, 100)}%;'
            f'background:{score_colour(report.score)}"></div></div>',
            unsafe_allow_html=True,
        )

    if result.profile and result.profile.total_experience_years:
        st.markdown(f"\n**Experience** · {result.profile.total_experience_years:.1f} years")

    links = result.links()
    if links:
        st.markdown("**Links found**")
        for kind, url in links.items():
            st.markdown(f"- [{kind.title()}]({url})")

    notes = result.enrichment_notes()
    if notes:
        st.markdown("**Link enrichment**")
        for key, note in notes.items():
            st.caption(f"{key}: {note}")


def render_candidate(result, job, position=None, expanded=False):
    report = result.report
    colour = score_colour(report.score)
    rank_html = f'<div class="tm-rank">#{position}</div>' if position else ""
    v = result.verdict
    pill = f'<span class="tm-pill p-{v.tone}">{v.label}</span>' if v else ""
    st.markdown(
        f'<div class="tm-card"><div class="tm-row">{rank_html}'
        f'<div class="tm-name">{result.display_name}<br>{pill}</div>'
        f'<div class="tm-score" style="color:{colour}">{report.score:.0f}'
        f"<small>/100</small></div></div></div>",
        unsafe_allow_html=True,
    )

    with st.expander("Evidence and detail", expanded=expanded):
        left, right = st.columns([2, 1])
        with left:
            render_evidence(result, job)
        with right:
            render_side_panel(result)
        if report.flags:
            st.markdown("**Needs a human look**")
            for flag in report.flags[:6]:
                st.warning(flag.detail)


def render_results(outcome, top_n):
    job = outcome.job
    render_requirements(job)
    ranked = outcome.ranked

    if not ranked:
        st.error("No resumes could be processed.")
        for f in outcome.failed:
            st.error(f"{f.display_name}: {f.error}")
        return

    if len(ranked) == 1:
        result = ranked[0]
        st.markdown(f"### {result.display_name}")
        colour = score_colour(result.report.score)
        st.markdown(
            f'<div class="tm-score" style="color:{colour}">'
            f"{result.report.score:.0f}<small>/100 against this JD</small></div>",
            unsafe_allow_html=True,
        )
        st.write("")
        render_verdict(result)
        st.divider()
        left, right = st.columns([2, 1])
        with left:
            st.markdown("#### Evidence against each requirement")
            render_evidence(result, job)
        with right:
            render_side_panel(result)
        if result.report.flags:
            st.markdown("#### Needs a human look")
            for flag in result.report.flags[:6]:
                st.warning(flag.detail)
    else:
        st.markdown(f"### Ranked shortlist · {len(ranked)} candidates reviewed")
        for i, result in enumerate(ranked[:top_n], start=1):
            render_candidate(result, job, position=i, expanded=(i == 1))

    if outcome.failed:
        with st.expander(f"{len(outcome.failed)} file(s) failed"):
            for f in outcome.failed:
                st.error(f"{f.display_name}: {f.error}")

    render_downloads(job, ranked)


def render_downloads(job, ranked):
    """Excel first — it is the format a recruiter forwards to a hiring manager."""
    st.divider()
    st.markdown("#### Export")

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_role = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in job.role_title
    )[:40]
    base = f"evaluation_{safe_role}_{stamp}"

    c1, c2, c3 = st.columns(3)

    with c1:
        workbook = to_excel(job, ranked)
        if workbook:
            st.download_button(
                "Excel workbook",
                data=workbook,
                file_name=f"{base}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            )
            st.caption("Ranking · Requirements · Job — three sheets")
        else:
            st.caption("Install openpyxl for the Excel export.")

    with c2:
        st.download_button(
            "Requirements (CSV)",
            data=to_csv(build_requirement_rows(job, ranked), REQUIREMENT_COLUMNS),
            file_name=f"{base}_requirements.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.caption("One row per candidate per requirement")

    with c3:
        st.download_button(
            "Ranking (CSV)",
            data=to_csv(build_ranking_rows(job, ranked), RANKING_COLUMNS),
            file_name=f"{base}_ranking.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.caption("One row per candidate")

    with st.expander("Preview the requirements table"):
        st.dataframe(
            build_requirement_rows(job, ranked),
            use_container_width=True,
            hide_index=True,
        )

    payload = {
        "role": job.role_title,
        "minimum_experience_years": job.minimum_experience_years,
        "candidates": [
            {
                "rank": i,
                "name": r.display_name,
                "score": r.report.score,
                "verdict": r.verdict.label if r.verdict else "",
                "breakdown": r.report.breakdown.model_dump(),
                "matches": [m.model_dump(mode="json") for m in r.report.matches],
                "flags": [f.model_dump() for f in r.report.flags],
            }
            for i, r in enumerate(ranked, start=1)
        ],
    }
    st.download_button(
        "Raw results (JSON)",
        data=json.dumps(payload, indent=2),
        file_name=f"{base}.json",
        mime="application/json",
    )


# ---------------------------------------------------------------------- main

def main():
    enrich, top_n = sidebar()
    jd_source, jd_is_text, paths = inputs()

    st.write("")
    ready = bool(jd_source) and bool(paths)
    if paths:
        label = "Review candidate" if len(paths) == 1 else f"Rank {len(paths)} candidates"
    else:
        label = "Review"

    if st.button(label, type="primary", disabled=not ready, use_container_width=True):
        bar = st.progress(0.0, text="Starting…")
        try:
            outcome = run(
                jd_source, paths, jd_is_text=jd_is_text, enrich=enrich,
                progress=lambda m, p: bar.progress(p, text=m),
            )
        except Exception as exc:
            bar.empty()
            st.error(f"Run failed: {exc}")
            return
        bar.empty()
        if not outcome.job:
            st.error(outcome.errors[0] if outcome.errors else "Could not read the JD.")
            return
        st.session_state["outcome"] = outcome

    if not ready:
        st.info("Add a job description and at least one resume to begin.")

    if "outcome" in st.session_state:
        st.divider()
        render_results(st.session_state["outcome"], top_n)


if __name__ == "__main__":
    main()
