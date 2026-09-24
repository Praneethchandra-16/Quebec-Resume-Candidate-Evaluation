"""
Render the synthetic candidates into data/resumes/*.pdf.

Links are written as real PDF link annotations (via ReportLab's <link> markup)
*and* as visible text, except for a couple of deliberate cases where only the
annotation carries the full URL. That lets us test both extraction paths.

Usage:
    python scripts/generate_resumes.py
"""

import sys
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.synthetic.candidates import CANDIDATES  # noqa: E402

OUT_DIR = ROOT / "data" / "resumes"

ACCENT = colors.HexColor("#1F3A5F")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "name", parent=ss["Title"], fontSize=18, leading=22,
            alignment=0, textColor=ACCENT, spaceAfter=2,
        ),
        "role": ParagraphStyle(
            "role", parent=ss["Normal"], fontSize=10.5, leading=13,
            textColor=colors.HexColor("#444444"), spaceAfter=4,
        ),
        "contact": ParagraphStyle(
            "contact", parent=ss["Normal"], fontSize=8.5, leading=12,
            textColor=colors.HexColor("#333333"),
        ),
        "section": ParagraphStyle(
            "section", parent=ss["Heading2"], fontSize=11, leading=13,
            textColor=ACCENT, spaceBefore=10, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body", parent=ss["Normal"], fontSize=9, leading=12,
            alignment=TA_JUSTIFY,
        ),
        "jobline": ParagraphStyle(
            "jobline", parent=ss["Normal"], fontSize=9.5, leading=12,
            spaceBefore=5,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=ss["Normal"], fontSize=8.8, leading=11.5,
        ),
    }


def _link(url: str, label: Optional[str] = None) -> str:
    """ReportLab markup producing a real PDF link annotation."""
    return f'<link href="{url}" color="#1155CC">{label or url}</link>'


def build_resume(c: dict, path: Path) -> None:
    st = _styles()
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"{c['name']} - Resume", author=c["name"],
    )
    s = []

    s.append(Paragraph(c["name"], st["name"]))
    s.append(Paragraph(c["title"], st["role"]))

    contact = [c["email"], c["phone"], c["location"]]
    s.append(Paragraph(" &nbsp;|&nbsp; ".join(contact), st["contact"]))

    # Links line. candidate_007's portfolio deliberately hides the scheme in the
    # visible text so only the annotation carries the full URL.
    link_bits = []
    for kind, url in c["links"].items():
        if c["id"] == "candidate_007" and kind == "portfolio":
            label = url.replace("https://", "")
        else:
            label = url
        link_bits.append(f"{kind.capitalize()}: {_link(url, label)}")
    if link_bits:
        s.append(Spacer(1, 2))
        s.append(Paragraph(" &nbsp;|&nbsp; ".join(link_bits), st["contact"]))

    s.append(Spacer(1, 4))
    s.append(HRFlowable(width="100%", thickness=0.7, color=ACCENT))

    s.append(Paragraph("SUMMARY", st["section"]))
    s.append(Paragraph(c["summary"], st["body"]))

    s.append(Paragraph("SKILLS", st["section"]))
    for group, items in c["skills"].items():
        s.append(Paragraph(f"<b>{group}:</b> {items}", st["body"]))

    s.append(Paragraph("PROFESSIONAL EXPERIENCE", st["section"]))
    for job in c["experience"]:
        s.append(Paragraph(
            f"<b>{job['title']}</b> - {job['company']} "
            f"<font color='#666666'>({job['dates']})</font>",
            st["jobline"],
        ))
        s.append(ListFlowable(
            [ListItem(Paragraph(b, st["bullet"]), leftIndent=10)
             for b in job["bullets"]],
            bulletType="bullet", start="\u2022", leftIndent=12,
            bulletFontSize=7, spaceBefore=2,
        ))

    if c["projects"]:
        s.append(Paragraph("PROJECTS", st["section"]))
        for p in c["projects"]:
            s.append(Paragraph(f"<b>{p['name']}</b> - {p['text']}", st["body"]))

    s.append(Paragraph("EDUCATION", st["section"]))
    for e in c["education"]:
        s.append(Paragraph(e, st["body"]))

    if c["certifications"]:
        s.append(Paragraph("CERTIFICATIONS", st["section"]))
        for cert in c["certifications"]:
            s.append(Paragraph(cert, st["body"]))

    doc.build(s)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for c in CANDIDATES:
        out = OUT_DIR / f"{c['id']}.pdf"
        build_resume(c, out)
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
