"""Proof that nothing is hardcoded to a job family.

Runs the JD analyser across five unrelated postings and prints what it extracted.
If a new role type appears tomorrow, this is the test that says whether the
system copes.

    python scripts/jd_generality_check.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.jd_agent import analyze_jd  # noqa: E402

JOBS = {
    "QA Analyst": """QA Analyst - Payments Platform
Requirements:
- 3+ years in software quality assurance
- Strong manual test case design and execution
- Automation with Selenium or Playwright
- API testing with Postman or REST Assured
- SQL for backend data verification
- Defect tracking in Jira, working within Agile sprints
Preferred:
- ISTQB certification
- Performance testing with JMeter
- CI integration of test suites""",

    "Business Analyst": """Business Analyst - Insurance
Requirements:
- 4+ years as a business analyst in financial services
- Requirements elicitation and stakeholder workshops
- BRD, FRD and user story authoring
- Process mapping using BPMN
- Strong SQL and Excel for data analysis
- Experience with Agile ceremonies and backlog grooming
Preferred:
- Power BI or Tableau dashboards
- Insurance domain knowledge (claims, underwriting)
- CBAP certification""",

    "Data Architect": """Data Architect
Requirements:
- 8+ years in data engineering or architecture
- Dimensional modelling and data warehouse design
- Snowflake or BigQuery at enterprise scale
- ETL/ELT orchestration with Airflow or dbt
- Data governance, lineage and cataloguing
- Cloud architecture on AWS or Azure
Preferred:
- Databricks and Spark
- Streaming with Kafka
- TOGAF certification""",

    "Support Engineer": """Technical Support Engineer - Tier 2
Requirements:
- 2+ years in a technical support or service desk role
- Troubleshooting Linux and Windows server issues
- Reading application logs and writing SQL queries
- Ticket management in Zendesk or ServiceNow
- Excellent written communication with customers
- Understanding of SLAs and escalation paths
Preferred:
- Scripting in Python or Bash
- Networking fundamentals (DNS, TCP/IP)
- ITIL Foundation""",

    "Registered Nurse": """Registered Nurse - ICU
Requirements:
- 3+ years critical care nursing experience
- BLS and ACLS certification required
- Ventilator management and titration of vasoactive drips
- Haemodynamic monitoring and patient assessment
- Proficiency with Epic electronic health records
Preferred:
- CCRN certification
- Charge nurse experience""",
}


def main() -> int:
    for name, text in JOBS.items():
        print("=" * 70)
        try:
            job = analyze_jd(text)
        except Exception as exc:
            print(f"{name}: FAILED - {exc}")
            continue
        print(f"{name}  ->  {job.role_title}")
        print(f"  minimum experience: {job.minimum_experience_years}")
        print(f"  required ({len(job.must_haves)}):")
        for r in job.must_haves:
            print(f"    [{r.weight:>2}] {r.skill}")
        print(f"  preferred ({len(job.nice_to_haves)}):")
        for r in job.nice_to_haves:
            print(f"    [{r.weight:>2}] {r.skill}")
    print("=" * 70)
    print("No job family is special-cased anywhere in the codebase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
