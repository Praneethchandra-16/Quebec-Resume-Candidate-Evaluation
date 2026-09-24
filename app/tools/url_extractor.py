"""URL normalisation + classification.

Resumes carry links in three ways: as PDF annotations, as full URLs in the text,
and as bare hostnames ('meerakrishnan.com'). We handle all three, then decide
what each link *is* so the right enrichment tool picks it up.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from app.schemas.candidate import LinkKind

# Full URLs, plus bare domains that look like a personal site.
URL_RE = re.compile(
    r"""(?xi)
    \b(
        (?:https?://|www\.)[^\s<>"'\)\]]+
        |
        (?:[a-z0-9][a-z0-9-]{1,60}\.)+(?:dev|io|ai|me|com|net|org|co|xyz|app)
        (?![a-z0-9.-])
        (?:/[^\s<>"'\)\]]*)?
    )
    """
)

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                   "utm_content", "fbclid", "gclid", "ref"}

# Hosts that are never a candidate's own profile/portfolio.
NOISE_HOSTS = {
    # mail + boilerplate
    "example.com", "gmail.com", "outlook.com", "yahoo.com", "hotmail.com",
    "w3.org", "adobe.com",
    # vendors/tools candidates name in bullets - not their own sites
    "microsoft.com", "openai.com", "python.org", "anthropic.com",
    "fly.io", "render.com", "railway.app", "heroku.com", "docker.com",
    "langchain.com", "streamlit.io", "qdrant.tech", "pinecone.io",
    "aws.amazon.com", "amazon.com", "azure.com", "google.com",
}

GITHUB_HOSTS = {"github.com", "gist.github.com"}
LINKEDIN_HOSTS = {"linkedin.com", "in.linkedin.com"}
CODE_OTHER_HOSTS = {
    "gitlab.com", "bitbucket.org", "huggingface.co", "kaggle.com",
    "stackoverflow.com", "medium.com", "dev.to", "scholar.google.com",
    "leetcode.com", "twitter.com", "x.com",
}


def normalise(url: str) -> str:
    """Lowercase host, force https, drop tracking params, strip trailing slash."""
    url = url.strip().rstrip(".,;)]}")
    if url.startswith("www."):
        url = "https://" + url
    if "://" not in url:
        url = "https://" + url

    parts = urlparse(url)
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    query = "&".join(
        kv for kv in parts.query.split("&")
        if kv and kv.split("=")[0].lower() not in TRACKING_PARAMS
    )
    path = parts.path.rstrip("/")

    return urlunparse(("https", host, path, "", query, ""))


def host_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_noise(url: str) -> bool:
    host = host_of(url)
    if host in NOISE_HOSTS:
        return True
    return any(host.endswith("." + n) for n in NOISE_HOSTS)


def classify(url: str) -> LinkKind:
    host = host_of(url)
    if host in GITHUB_HOSTS or host.endswith(".github.io"):
        return LinkKind.GITHUB
    if host in LINKEDIN_HOSTS or host.endswith(".linkedin.com"):
        return LinkKind.LINKEDIN
    if host in CODE_OTHER_HOSTS:
        return LinkKind.OTHER
    if is_noise(url):
        return LinkKind.OTHER
    # Personal site heuristic: short host, not a known platform.
    return LinkKind.PORTFOLIO


def extract_urls_from_text(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in URL_RE.finditer(text):
        raw = m.group(1)
        # Skip anything that is actually the domain part of an email.
        start = m.start(1)
        if start > 0 and text[start - 1] == "@":
            continue
        url = normalise(raw)
        if is_noise(url) or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def github_username(url: str) -> str | None:
    if classify(url) != LinkKind.GITHUB:
        return None
    host = host_of(url)
    if host.endswith(".github.io"):
        return host.split(".")[0]
    parts = [p for p in urlparse(url).path.split("/") if p]
    return parts[0] if parts else None
