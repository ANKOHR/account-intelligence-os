from __future__ import annotations

import json
from pathlib import Path

from aios.adapters import detect_tech_signals, parse_github_json, parse_html_evidence, parse_news_json
from aios.fixtures import FIXTURE_ROOT


def test_fixture_html_parses_to_evidence_records():
    html = (FIXTURE_ROOT / "home.html").read_text(encoding="utf-8")
    records = parse_html_evidence(html, "https://northstar-ledger.example/", "2026-09-27")
    assert len(records) == 1
    assert "routes invoices from upload through approval" in records[0].snippet
    assert records[0].source_url == "https://northstar-ledger.example/"
    assert records[0].retrieved_at == "2026-09-27"


def test_fixture_news_json_parses_to_evidence_records():
    payload = (FIXTURE_ROOT / "news.json").read_text(encoding="utf-8")
    records = parse_news_json(payload, "https://northstar-ledger.example/news/", "2026-09-27")
    assert len(records) == 1
    assert "2026-09-09" in records[0].snippet
    assert records[0].source_url.endswith("/news/reconciliation-assistant-pilot")


def test_fixture_github_json_parses_to_evidence_records():
    payload = (FIXTURE_ROOT / "github.json").read_text(encoding="utf-8")
    records = parse_github_json(payload, "https://api.github.com/orgs/demo/repos", "2026-09-27")
    assert len(records) == 2
    assert json.loads(records[0].snippet)["name"] == "ledger-connectors"
    assert records[0].source_url == "https://api.github.com/orgs/demo/repos"


def test_malformed_html_json_and_github_data_are_handled():
    assert parse_html_evidence("", "https://example.com", "2026-09-27") == []
    assert parse_html_evidence(None, "https://example.com", "2026-09-27") == []
    assert parse_news_json("{not json", "https://example.com/news", "2026-09-27") == []
    assert parse_news_json('{"items": "wrong"}', "https://example.com/news", "2026-09-27") == []
    assert parse_github_json("not json", "https://api.github.com/repos", "2026-09-27") == []
    assert parse_github_json('[{"bad": true}, null]', "https://api.github.com/repos", "2026-09-27") == []


def test_tech_signals_are_literal_markup_references():
    html = '<script src="/react.production.min.js"></script>'
    records = detect_tech_signals(html, "https://example.com", "2026-09-27")
    assert len(records) == 1
    assert records[0].source_kind == "tech_signal:React"
    assert records[0].snippet == "/react.production.min.js"


def test_html_page_text_skips_script_contents():
    records = parse_html_evidence(
        "<main>Visible copy</main><script>secret fact()</script>",
        "https://example.com",
        "2026-09-27",
    )
    assert records[0].snippet == "Visible copy"
