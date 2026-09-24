import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schemas.candidate import LinkKind  # noqa: E402
from app.tools.pdf_parser import parse_resume  # noqa: E402
from app.tools.url_extractor import (  # noqa: E402
    classify,
    extract_urls_from_text,
    github_username,
    normalise,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://www.LinkedIn.com/in/foo/", "https://linkedin.com/in/foo"),
        ("github.com/bar", "https://github.com/bar"),
        ("www.baz.dev", "https://baz.dev"),
        ("https://x.dev/p?utm_source=cv&id=3", "https://x.dev/p?id=3"),
    ],
)
def test_normalise(raw, expected):
    assert normalise(raw) == expected


@pytest.mark.parametrize(
    "url,kind",
    [
        ("https://github.com/foo", LinkKind.GITHUB),
        ("https://foo.github.io", LinkKind.GITHUB),
        ("https://linkedin.com/in/foo", LinkKind.LINKEDIN),
        ("https://foo.dev", LinkKind.PORTFOLIO),
        ("https://medium.com/@foo", LinkKind.OTHER),
    ],
)
def test_classify(url, kind):
    assert classify(url) == kind


def test_email_domain_is_not_a_url():
    text = "Contact: aarav.menon@example.com"
    assert extract_urls_from_text(text) == []


def test_vendor_names_are_not_portfolios():
    text = "Deployed to Fly.io and monitored with langchain.com tooling."
    assert extract_urls_from_text(text) == []


def test_github_username():
    assert github_username("https://github.com/aaravmenon") == "aaravmenon"
    assert github_username("https://github.com/foo/bar") == "foo"
    assert github_username("https://linkedin.com/in/foo") is None


@pytest.mark.parametrize("path", sorted((ROOT / "data" / "resumes").glob("*.pdf")))
def test_every_resume_parses(path):
    parsed = parse_resume(path, "CAND-TEST")
    assert len(parsed.text) > 800
    assert parsed.contact.email and "@" in parsed.contact.email
    assert parsed.links, f"no links found in {path.name}"


def test_hidden_scheme_link_is_recovered_from_annotation():
    """candidate_007's portfolio is displayed without https:// in the text."""
    parsed = parse_resume(ROOT / "data" / "resumes" / "candidate_007.pdf", "CAND-007")
    portfolios = [link for link in parsed.links if link.kind == LinkKind.PORTFOLIO]
    assert any(link.url == "https://meerakrishnan.com" for link in portfolios)
