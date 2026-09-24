# Quebec Candidate Resume Evaluation — evidence-grounded candidate review

An agentic screening system that reads a job description, parses resumes,
follows the links inside them (GitHub, portfolio), matches each JD requirement
to **evidence** rather than keywords, and produces a ranked, explainable
shortlist for a human recruiter.

The system does not decide who to hire. It surfaces job-relevant evidence,
gaps and flags, and a recruiter makes the call.

## Pipeline

```
JD ──► JD Analyzer ──► structured requirements (weighted, atomic, aliased)
                                    │
resumes ──► parser ──► profile ──► link enrichment ──► matcher ──► validator
            (no LLM)     (LLM)      (GitHub API,        (LLM)      (Python)
                                     portfolio fetch)      │
                                                           ▼
                                      Python scoring ──► report ──► recruiter UI
```

Two rules the whole design hangs on:

1. **The LLM extracts and classifies. Python scores.** No prompt ever returns a
   final number. That keeps ranking reproducible, testable and auditable.
2. **Evidence has a strength.** "LangGraph" in a skills list is not the same as
   "shipped a LangGraph workflow serving 180k requests/month", and the scale in
   `app/schemas/evidence.py` encodes that difference.

## Status

| Step | What | State |
|---|---|---|
| 1 | Schemas, synthetic dataset, deterministic parsing | **done** |
| 2 | JD Analyzer + Resume Extractor (structured outputs) | **done** |
| 3 | Blinding, skill ontology, evidence matcher | **done** |
| 4 | Validator + deterministic scoring | **done** |
| 5 | Streamlit recruiter dashboard | **done** |
| 6 | GitHub / portfolio enrichment, LinkedIn handler | **done** |
| 7 | Verdict + feedback for single-candidate review | **done** |
| 8 | Evaluation harness against ground truth | next |
| 9 | LangGraph orchestration + FastAPI + Docker | |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in keys when you reach step 2
```

## Run it

```bash
streamlit run frontend/streamlit_app.py
```

Paste any job description, upload any resumes, get a ranked list. It works with
no API key at all — the sidebar defaults to an offline keyword baseline. Switch
the provider to OpenAI or Anthropic in the sidebar (with a key in `.env`) for
real evidence grading.

Command line, if you want it:

```bash
python scripts/generate_resumes.py     # rebuild the 8 synthetic resume PDFs
python scripts/step1_parse_check.py    # parse them, print text stats + links
pytest -q                              # 32 tests
```

## How the score is built

Nothing in the scorer knows what "LangGraph" is. The JD agent extracts weighted
requirements from whatever job description you supply, and the score is computed
from those weights:

| Component | Points |
|---|---|
| Must-have coverage | 70 |
| Nice-to-have coverage | 10 |
| Experience fit | 15 |
| Verified external evidence | 5 |

Each requirement earns its weight times a multiplier set by evidence strength —
`MENTIONED` earns 0.25, `STRONG_PRODUCTION_EVIDENCE` earns 1.0. That one table is
the whole difference between this and keyword matching: a resume listing thirty
technologies with no described work tops out around a quarter of the available
points.

Swap in a nursing JD or a sales JD and the requirements, weights and scoring
basis all change with it. Nothing is hardcoded to AI roles.

## The synthetic dataset

One JD (`data/jd/senior_ai_engineer.md`) and eight resumes designed so that a
naive keyword or cosine-similarity system gets the ranking *wrong*:

| # | Persona | What it tests |
|---|---|---|
| 001 | Strong agentic AI engineer | the obvious top result |
| 002 | Strong classical ML, thin GenAI | seniority ≠ relevance |
| 003 | Deep GenAI, no production/cloud | depth vs. deployability |
| 004 | Strong backend/cloud, moderate AI | partial-fit handling |
| 005 | Excellent RAG work, only 2 years | experience gate should cap, not delete |
| 006 | Keyword-stuffed, no accomplishments | **must not** reach the top 3 |
| 007 | Plain resume, excellent GitHub | link enrichment must move them up |
| 008 | Data analyst | clear non-fit |

`data/synthetic/ground_truth.json` holds hand-labelled evidence strengths per
candidate per requirement, plus the expected rank order. From step 6 the
evaluation harness scores the pipeline against it: extraction precision/recall,
requirement-classification accuracy, URL accuracy, hallucination rate, and
rank correlation.

To edit a persona, change `data/synthetic/candidates.py` and re-run the
generator — the PDFs are build artefacts, not source.

## Layout

```
app/
  schemas/    job.py, candidate.py, evidence.py   <- the data contract
  tools/      pdf_parser.py, url_extractor.py     <- deterministic, no LLM
  agents/     (step 2+) jd, resume, github, portfolio, matcher, report
  graph/      (step 6) state.py, nodes.py, workflow.py
  scoring/    (step 5) criteria.py, demo_score.py
  services/   (step 8) embeddings.py, vector_store.py
  api/        (step 7) main.py
data/
  jd/         the job description
  resumes/    generated PDFs (build artefact)
  synthetic/  candidates.py, ground_truth.json    <- source of truth
scripts/      generators and per-step check scripts
tests/
```

## Exports

Every run produces a downloadable workbook with three sheets:

| Sheet | One row per | Key columns |
|---|---|---|
| Ranking | candidate | rank, score, verdict, coverage %, required vs actual experience, points breakdown, links |
| Requirements | candidate x requirement | requirement, must/nice, weight, evidence level, **Satisfied** (Yes/Partial/Weak/No), the quote, its source |
| Job | — | what the system read out of the posting |

The Satisfied column is colour-coded, panes are frozen and filters are on, so a
recruiter can sort by "must-have + No" and see every gap in one view. Experience
gets its own row stating the comparison plainly, e.g. *"JD asks for 5+ years;
resume shows 6.5."* CSV and JSON exports are available alongside it.

## Deploying it

The app runs locally with `streamlit run frontend/streamlit_app.py`, which serves
on localhost only and stops when the process does. For a permanent public link,
push this repo to GitHub and deploy on Streamlit Community Cloud:

1. Sign in at share.streamlit.io with GitHub.
2. Pick this repo, branch `main`, main file path `frontend/streamlit_app.py`.
3. Under Advanced settings, add any API keys as secrets (`OPENAI_API_KEY`,
   `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`). The app reads Streamlit secrets and
   environment variables interchangeably, so nothing in the code changes.

With no keys configured the app still works — it falls back to the offline
keyword baseline, which is why the deployed demo never shows an error page to a
first-time visitor.

## Any job, not just this one

There is no job-family logic anywhere in the codebase. The JD agent reads
whatever posting you give it, extracts weighted requirements, and the scorer does
arithmetic over those weights. `scripts/jd_generality_check.py` runs five
unrelated postings — QA Analyst, Business Analyst, Data Architect, Support
Engineer, ICU Nurse — and prints what came out of each.

## Notes on the real world

- **LinkedIn is not scraped.** Their User Agreement prohibits automated
  crawling of profiles, and the official Profile API is limited to approved
  partners. The system records that a LinkedIn URL exists and stops there; a
  recruiter opens it manually. For the demo, dummy profile text can be supplied.
- **GitHub is supplementary evidence, never a requirement.** Plenty of strong
  engineers cannot publish employer work.
- **Blinding.** Name, contact details, photo, age, gender and address are
  stripped before any qualification analysis; the matcher only sees `CAND-00X`
  plus job-relevant content.
- **Flags, not verdicts.** Timeline impossibilities (e.g. "5 years of LangGraph")
  and unverifiable quotes are raised for recruiter checking rather than silently
  penalised.
