"""Step 1 check: parse every resume, print text stats, links and contact fields.

No API key needed. If this is not clean, do not move on to the LLM stages.

Usage:
    python scripts/step1_parse_check.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.tools.pdf_parser import parse_resume  # noqa: E402

RESUMES = sorted((ROOT / "data" / "resumes").glob("*.pdf"))


def main() -> int:
    if not RESUMES:
        print("No resumes found. Run scripts/generate_resumes.py first.")
        return 1

    failures = 0
    for i, path in enumerate(RESUMES, start=1):
        cid = f"CAND-{i:03d}"
        parsed = parse_resume(path, cid)

        print(f"\n{'=' * 68}")
        print(f"{cid}  <-  {path.name}")
        print(f"  pages={parsed.page_count}  chars={len(parsed.text)}")
        print(f"  name={parsed.contact.name!r}")
        print(f"  email={parsed.contact.email!r}  phone={parsed.contact.phone!r}")
        print("  links:")
        if not parsed.links:
            print("    (none)")
        for link in parsed.links:
            print(f"    [{link.kind.value:<9}] {link.url}  ({link.source})")

        if len(parsed.text) < 500:
            print("  !! suspiciously little text extracted")
            failures += 1

    print(f"\n{'=' * 68}")
    print(f"Parsed {len(RESUMES)} resumes, {failures} suspicious.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
