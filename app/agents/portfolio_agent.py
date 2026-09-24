"""Portfolio fetching, and the LinkedIn policy boundary.

Portfolio: fetch a small number of pages from the candidate's own domain and
reduce them to plain text. Same-origin only, capped page count, short timeout,
robots.txt respected. A candidate's site is not a crawl target.

LinkedIn: not fetched. LinkedIn's User Agreement prohibits automated scraping of
profiles, and their Profile API is limited to approved partners. The system
records that the URL exists, surfaces it for a human to open, and stops. If your
organisation has an approved integration, that is where it plugs in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin, urlparse

CANDIDATE_PATHS = ["", "/projects", "/work", "/about", "/portfolio", "/experience"]
MAX_PAGES = 4
MAX_CHARS = 6000


@dataclass
class PortfolioEvidence:
    url: str = ""
    ok: bool = False
    error: str = ""
    pages_fetched: List[str] = field(default_factory=list)
    text: str = ""

    def as_text(self) -> str:
        return self.text if self.ok else ""

    def summary(self) -> str:
        if not self.ok:
            return self.error or "Not retrieved."
        return f"{len(self.pages_fetched)} page(s) read from the candidate's site."


def _allowed_by_robots(base: str, path: str) -> bool:
    import urllib.robotparser as rp

    try:
        parser = rp.RobotFileParser()
        parser.set_url(urljoin(base, "/robots.txt"))
        parser.read()
        return parser.can_fetch("quebec-candidate-resume-evaluation", urljoin(base, path))
    except Exception:
        return True  # no robots.txt, or unreachable: proceed politely


def _page_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return " ".join(text.split())


def analyze_portfolio(url: str, timeout: int = 10) -> PortfolioEvidence:
    """Read a candidate's personal site. Never raises."""
    import httpx

    ev = PortfolioEvidence(url=url)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        ev.error = "Not a usable portfolio URL."
        return ev

    base = f"{parsed.scheme}://{parsed.netloc}"
    chunks: List[str] = []

    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "quebec-candidate-resume-evaluation (recruiting assistant)"},
        ) as client:
            for path in CANDIDATE_PATHS:
                if len(ev.pages_fetched) >= MAX_PAGES:
                    break
                target = urljoin(base, path) if path else url
                if not _allowed_by_robots(base, path or "/"):
                    continue
                try:
                    resp = client.get(target)
                except Exception:
                    continue
                if resp.status_code != 200 or "html" not in resp.headers.get(
                    "content-type", ""
                ):
                    continue
                text = _page_text(resp.text)
                if len(text) < 80:
                    continue
                chunks.append(f"From {target}: {text}")
                ev.pages_fetched.append(target)
                if sum(len(c) for c in chunks) > MAX_CHARS:
                    break
    except Exception as exc:
        ev.error = f"Portfolio fetch failed: {exc}"
        return ev

    if not chunks:
        ev.error = "No readable pages found. The site may be JavaScript-rendered."
        return ev

    ev.text = "\n".join(chunks)[:MAX_CHARS]
    ev.ok = True
    return ev


@dataclass
class LinkedInEvidence:
    url: str = ""
    ok: bool = False
    note: str = ""

    def as_text(self) -> str:
        return ""

    def summary(self) -> str:
        return self.note


def handle_linkedin(url: Optional[str], pasted_text: Optional[str] = None):
    """Records the URL. Optionally accepts profile text a recruiter pasted in
    themselves, which is permitted where automated retrieval is not."""
    if not url:
        return LinkedInEvidence(note="No LinkedIn URL found in the resume.")
    ev = LinkedInEvidence(url=url)
    if pasted_text and len(pasted_text.strip()) > 100:
        ev.ok = True
        ev.note = "Profile text supplied manually by the recruiter."
        ev.__dict__["text"] = pasted_text.strip()
        return ev
    ev.note = (
        "LinkedIn URL detected. Not retrieved automatically: LinkedIn's terms "
        "prohibit automated profile scraping. Open it manually to review."
    )
    return ev
