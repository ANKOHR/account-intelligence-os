"""Load the bundled fictional company through the same parsers as live sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters import detect_tech_signals, parse_github_json, parse_html_evidence, parse_news_json
from .models import EvidenceRecord, TargetSpec


FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"


def fixture_metadata() -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / "company.json").read_text(encoding="utf-8"))


def fixture_target() -> TargetSpec:
    return TargetSpec.from_dict(fixture_metadata()["target"])


def load_fixture_evidence() -> tuple[list[EvidenceRecord], list[str]]:
    """Parse fixture HTML and JSON without importing or calling any network client."""
    metadata = fixture_metadata()
    target = TargetSpec.from_dict(metadata["target"])
    retrieved_at = str(metadata["retrieved_at"])
    root = f"https://{target.domain}"
    records: list[EvidenceRecord] = []

    home = (FIXTURE_ROOT / "home.html").read_text(encoding="utf-8")
    about = (FIXTURE_ROOT / "about.html").read_text(encoding="utf-8")
    careers = (FIXTURE_ROOT / "careers.html").read_text(encoding="utf-8")
    news = (FIXTURE_ROOT / "news.json").read_text(encoding="utf-8")
    github = (FIXTURE_ROOT / "github.json").read_text(encoding="utf-8")

    records.extend(parse_html_evidence(home, root + "/", retrieved_at, "company_site"))
    records.extend(detect_tech_signals(home, root + "/", retrieved_at))
    records.extend(parse_html_evidence(about, root + "/about", retrieved_at, "company_site"))
    records.extend(parse_news_json(news, root + "/news/", retrieved_at))
    records.extend(parse_html_evidence(careers, root + "/careers", retrieved_at, "careers"))
    github_endpoint = "https://api.github.com/orgs/northstar-ledger-example/repos?per_page=100"
    records.extend(parse_github_json(github, github_endpoint, retrieved_at))
    return records, []
