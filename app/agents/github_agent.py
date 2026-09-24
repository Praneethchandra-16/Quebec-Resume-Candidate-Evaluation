"""GitHub enrichment.

Turns a GitHub URL into text evidence the matcher can quote from and the
validator can verify. Uses the public REST API rather than scraping HTML, so it
stays within GitHub's terms and does not break when their markup changes.

Deliberate limits:
  - Unauthenticated calls are rate-limited to 60/hour. Set GITHUB_TOKEN to get
    5000/hour. Without one, a batch of 50 resumes will hit the ceiling.
  - Stars are recorded but weighted at nothing. Popularity is not competence.
  - Absence of a GitHub profile is never penalised. Most professional work
    cannot be published, and plenty of strong engineers have empty accounts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.config import get_settings
from app.tools.url_extractor import github_username

API = "https://api.github.com"
_CACHE: Dict[str, "GitHubEvidence"] = {}


@dataclass
class Repo:
    name: str
    description: str = ""
    language: str = ""
    topics: List[str] = field(default_factory=list)
    stars: int = 0
    updated: str = ""
    readme_excerpt: str = ""
    is_fork: bool = False


@dataclass
class GitHubEvidence:
    username: str = ""
    url: str = ""
    ok: bool = False
    error: str = ""
    public_repos: int = 0
    followers: int = 0
    bio: str = ""
    repos: List[Repo] = field(default_factory=list)

    def as_text(self) -> str:
        """Flat text block. The matcher quotes from this; the validator checks
        quotes against this exact string, so format changes must stay in sync."""
        if not self.ok:
            return ""
        lines = [f"GitHub profile {self.url} with {self.public_repos} public repositories."]
        if self.bio:
            lines.append(f"Profile bio: {self.bio}")
        for r in self.repos:
            bits = [f"Repository {r.name}."]
            if r.description:
                bits.append(f"Description: {r.description}")
            if r.language:
                bits.append(f"Primary language: {r.language}.")
            if r.topics:
                bits.append("Topics: " + ", ".join(r.topics) + ".")
            if r.updated:
                bits.append(f"Last updated {r.updated[:10]}.")
            if r.readme_excerpt:
                bits.append(f"README says: {r.readme_excerpt}")
            lines.append(" ".join(bits))
        return "\n".join(lines)

    def summary(self) -> str:
        if not self.ok:
            return self.error or "Not retrieved."
        active = [r for r in self.repos if not r.is_fork]
        return (
            f"{self.public_repos} public repositories, "
            f"{len(active)} original repos examined."
        )


def _get(path: str, token: str, timeout: int = 15):
    import httpx

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "quebec-candidate-resume-evaluation"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = httpx.get(f"{API}{path}", headers=headers, timeout=timeout, follow_redirects=True)
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RuntimeError(
            "GitHub API rate limit reached. Add GITHUB_TOKEN to .env to raise it."
        )
    resp.raise_for_status()
    return resp.json()


def _readme(username: str, repo: str, token: str, limit: int = 700) -> str:
    import base64

    try:
        data = _get(f"/repos/{username}/{repo}/readme", token)
        raw = base64.b64decode(data.get("content", "")).decode("utf-8", "ignore")
    except Exception:
        return ""
    # Strip markdown noise so quotes stay readable and verifiable.
    cleaned = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(("![", "[!", "<img", "---", "|")):
            continue
        cleaned.append(line.lstrip("#").strip())
        if sum(len(c) for c in cleaned) > limit:
            break
    return " ".join(cleaned)[:limit]


def analyze_github(
    url: str, max_repos: int = 8, fetch_readmes: bool = True
) -> GitHubEvidence:
    """Fetch a candidate's public GitHub activity. Never raises."""
    username = github_username(url)
    if not username:
        return GitHubEvidence(url=url, error="Not a recognisable GitHub profile URL.")
    if username in _CACHE:
        return _CACHE[username]

    token = get_settings().github_token
    ev = GitHubEvidence(username=username, url=url)

    try:
        profile = _get(f"/users/{username}", token)
        ev.public_repos = profile.get("public_repos", 0) or 0
        ev.followers = profile.get("followers", 0) or 0
        ev.bio = (profile.get("bio") or "").strip()

        repos = _get(f"/users/{username}/repos?sort=pushed&per_page=30", token)
        repos = [r for r in repos if not r.get("fork")] or repos
        for r in repos[:max_repos]:
            repo = Repo(
                name=r.get("name", ""),
                description=(r.get("description") or "").strip(),
                language=r.get("language") or "",
                topics=r.get("topics") or [],
                stars=r.get("stargazers_count", 0),
                updated=r.get("pushed_at") or "",
                is_fork=bool(r.get("fork")),
            )
            if fetch_readmes and len(ev.repos) < 4:
                repo.readme_excerpt = _readme(username, repo.name, token)
                time.sleep(0.1)
            ev.repos.append(repo)
        ev.ok = True
    except Exception as exc:
        ev.error = f"GitHub lookup failed: {exc}"

    _CACHE[username] = ev
    return ev


def clear_cache() -> None:
    _CACHE.clear()
