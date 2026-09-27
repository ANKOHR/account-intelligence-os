"""Stdlib evidence adapters for web pages, news, careers, GitHub, and tech hints."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from .models import AdapterResult, EvidenceRecord, TargetSpec


class _TextExtractor(HTMLParser):
    _blocked_tags = {"script", "style", "noscript", "svg", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.in_title = False
        self.blocked_depth = 0
        self.title: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() in self._blocked_tags:
            self.blocked_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False
        if tag.lower() in self._blocked_tags and self.blocked_depth:
            self.blocked_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.blocked_depth:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)
            if self.in_title:
                self.title.append(cleaned)


def parse_html_evidence(
    html: str,
    source_url: str,
    retrieved_at: str,
    source_kind: str = "company_site",
) -> list[EvidenceRecord]:
    """Parse readable page text into one evidence record; tolerate broken markup."""
    if not isinstance(html, str) or not html.strip() or not source_url.strip():
        return []
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except (ValueError, AssertionError):
        return []
    body = " ".join(parser.parts)
    if not body:
        return []
    title = " ".join(parser.title)
    snippet = body[:1200]
    if title and title not in snippet:
        snippet = f"{title}. {snippet}"[:1200]
    return [EvidenceRecord(source_url, retrieved_at, snippet, source_kind)]


def parse_news_json(
    payload: str | bytes | dict[str, Any], source_url: str, retrieved_at: str
) -> list[EvidenceRecord]:
    """Convert a small news feed JSON document into source-backed records."""
    try:
        data = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return []
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return []
    records: list[EvidenceRecord] = []
    for item in data["items"]:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        summary = item.get("summary")
        published = item.get("date")
        if not all(isinstance(value, str) and value.strip() for value in (title, summary, published)):
            continue
        item_url = item.get("url")
        item_source = urljoin(source_url, item_url) if isinstance(item_url, str) and item_url else source_url
        snippet = f"{published.strip()}: {title.strip()}. {summary.strip()}"
        records.append(EvidenceRecord(item_source, retrieved_at, snippet[:1200], "news"))
    return records


def parse_github_json(
    payload: str | bytes | list[Any], source_url: str, retrieved_at: str
) -> list[EvidenceRecord]:
    """Extract public repository metadata from the GitHub organization API shape."""
    try:
        data = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    records: list[EvidenceRecord] = []
    for repo in data:
        if not isinstance(repo, dict) or not isinstance(repo.get("name"), str):
            continue
        metadata = {
            "name": repo["name"],
            "html_url": repo.get("html_url", ""),
            "language": repo.get("language"),
        }
        records.append(
            EvidenceRecord(
                source_url,
                retrieved_at,
                json.dumps(metadata, sort_keys=True, separators=(",", ":")),
                "github",
            )
        )
    return records


_TECH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("React", re.compile(r"(?:src|href)\s*=\s*[\"']([^\"']*react[^\"']*)[\"']", re.I)),
    (
        "Google tag loader",
        re.compile(r"(https?://www\.googletagmanager\.com/gtag/js[^\"'\s<>]*)", re.I),
    ),
    ("HubSpot tracking script", re.compile(r"(https?://js\.hs-scripts\.com/[^\"'\s<>]+)", re.I)),
)


def detect_tech_signals(html: str, source_url: str, retrieved_at: str) -> list[EvidenceRecord]:
    """Return only literal technology references visible in page markup."""
    if not isinstance(html, str):
        return []
    found: list[EvidenceRecord] = []
    for label, pattern in _TECH_PATTERNS:
        for match in pattern.findall(html):
            quote_text = str(match).strip()
            found.append(
                EvidenceRecord(
                    source_url,
                    retrieved_at,
                    quote_text,
                    f"tech_signal:{label}",
                )
            )
    return found


def fetch_url(url: str, timeout: float = 5.0) -> bytes:
    """Fetch one public page using the standard library."""
    request = Request(
        url,
        headers={"User-Agent": "AccountIntelligenceOS/0.1 (+offline-fixture-supported)"},
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read(2_000_000)


def _fetch_page(url: str, retrieved_at: str, kind: str) -> tuple[list[EvidenceRecord], list[EvidenceRecord], str]:
    try:
        raw = fetch_url(url)
        html = raw.decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        reason = getattr(exc, "reason", None) or str(exc)
        return [], [], f"{kind}: unavailable ({type(exc).__name__}: {reason})"
    return (
        parse_html_evidence(html, url, retrieved_at, kind),
        detect_tech_signals(html, url, retrieved_at),
        "",
    )


class EvidenceAdapter(Protocol):
    """Interface for an injectable evidence source adapter."""

    name: str

    def collect(self, target: TargetSpec, retrieved_at: str) -> AdapterResult:
        """Collect evidence records and source availability details."""


class CompanyWebAdapter:
    """Fetch the homepage, about, news, and careers pages for a target."""

    name = "company_web"

    def collect(self, target: TargetSpec, retrieved_at: str) -> AdapterResult:
        records: list[EvidenceRecord] = []
        unavailable: list[str] = []
        root = f"https://{target.domain}"
        for path, kind in (("/", "company_site"), ("/about", "company_site"), ("/news", "news"), ("/careers", "careers")):
            page_records, tech_records, error = _fetch_page(urljoin(root, path), retrieved_at, kind)
            records.extend(page_records)
            records.extend(tech_records)
            if error:
                unavailable.append(error)
        return AdapterResult(tuple(records), tuple(unavailable))


class GitHubOrganizationAdapter:
    """Fetch public repositories for an explicitly configured organization."""

    name = "github"

    def collect(self, target: TargetSpec, retrieved_at: str) -> AdapterResult:
        if not target.github_org:
            return AdapterResult(unavailable=("github: unavailable (organization not configured)",))
        endpoint = f"https://api.github.com/orgs/{quote(target.github_org, safe='')}/repos?per_page=100"
        try:
            payload = fetch_url(endpoint).decode("utf-8", errors="replace")
            repos = parse_github_json(payload, endpoint, retrieved_at)
            if repos:
                return AdapterResult(tuple(repos))
            return AdapterResult(unavailable=("github: unavailable (no parseable public repository data)",))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            reason = getattr(exc, "reason", None) or str(exc)
            return AdapterResult(unavailable=(f"github: unavailable ({type(exc).__name__}: {reason})",))


def collect_live_evidence(
    target: TargetSpec,
    retrieved_at: str,
    adapters: tuple[EvidenceAdapter, ...] | None = None,
) -> AdapterResult:
    """Collect evidence through pluggable adapters; failures degrade to status."""
    selected = adapters if adapters is not None else (CompanyWebAdapter(), GitHubOrganizationAdapter())
    records: list[EvidenceRecord] = []
    unavailable: list[str] = []
    for adapter in selected:
        try:
            result = adapter.collect(target, retrieved_at)
        except Exception as exc:
            unavailable.append(f"{adapter.name}: unavailable ({type(exc).__name__}: {exc})")
            continue
        records.extend(result.records)
        unavailable.extend(result.unavailable)
    return AdapterResult(tuple(records), tuple(unavailable))
