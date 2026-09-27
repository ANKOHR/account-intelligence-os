from __future__ import annotations

from dataclasses import asdict

import pytest

from aios import adapters
from aios.claims import claim_from_evidence
from aios.fixtures import load_fixture_evidence
from aios.models import AdapterResult, Claim, EvidenceRecord, ProvenanceError, TargetSpec
from aios.pipeline import build_dossier
from aios.render import render_markdown
from aios.scoring import score_opportunities


def test_every_built_claim_has_source_url_and_date():
    dossier = build_dossier(fixture=True)
    assert dossier.claims
    for claim in dossier.claims:
        assert claim.source_url.startswith(("https://", "http://"))
        assert claim.retrieved_at == "2026-09-27"
        assert claim.supporting_quote


def test_claim_without_provenance_is_rejected():
    with pytest.raises(ProvenanceError, match="source_url"):
        Claim(
            claim_id="claim-bad",
            statement="An unsupported fact",
            source_url="",
            retrieved_at="2026-09-27",
            supporting_quote="A quote with no source",
            source_kind="company_site",
        )
    with pytest.raises(ProvenanceError, match="retrieved_at"):
        claim_from_evidence(EvidenceRecord("https://example.com", "unknown", "A statement", "company_site"))


def test_scoring_is_deterministic_for_identical_fixture_evidence():
    records, _ = load_fixture_evidence()
    from aios.claims import extract_claims

    claims = extract_claims(records)
    first = [item.to_dict() for item in score_opportunities(claims)]
    second = [item.to_dict() for item in score_opportunities(claims)]
    assert first == second
    assert [item["opportunity_id"] for item in first] == [item["opportunity_id"] for item in second]


def test_dossier_has_all_required_sections_and_explicit_unknowns():
    dossier = build_dossier(fixture=True)
    required = {
        "profile",
        "recent_developments",
        "tech_stack",
        "probable_pain_points",
        "outreach_angle",
        "call_briefing",
        "objection_prep",
        "follow_up_ideas",
        "unknowns",
    }
    assert required.issubset(dossier.sections)
    assert any("unknown" in item.lower() for item in dossier.sections["unknowns"])
    assert "reconciliation assistant" in dossier.sections["outreach_angle"]["hook"].lower()
    markdown = render_markdown(dossier)
    for heading in (
        "Company profile", "Recent developments", "Tech stack signals", "Probable pain points",
        "Ranked opportunities", "Outreach angle", "Call briefing", "Objection prep", "Follow-up ideas", "Unknowns",
    ):
        assert f"## {heading}" in markdown
    assert markdown.startswith("> **FICTIONAL FIXTURE:")


def test_fixture_pipeline_never_calls_network_fetcher(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("fixture pipeline attempted a network request")

    monkeypatch.setattr(adapters, "fetch_url", forbidden)
    dossier = build_dossier(fixture=True)
    assert dossier.claims
    assert "FICTIONAL FIXTURE" in dossier.fixture_notice


def test_live_source_adapters_are_injectable():
    record = EvidenceRecord("https://example.com", "2026-09-27", "Source-backed note", "custom")

    class CustomAdapter:
        name = "custom"

        def collect(self, target, retrieved_at):
            assert target.company == "Example Co"
            assert retrieved_at == "2026-09-27"
            return AdapterResult(records=(record,))

    result = adapters.collect_live_evidence(
        TargetSpec("Example Co", "example.com"),
        "2026-09-27",
        adapters=(CustomAdapter(),),
    )
    assert result.records == (record,)
    assert result.unavailable == ()


def test_fixture_target_mismatch_is_rejected():
    from aios.models import TargetSpec

    with pytest.raises(ValueError, match="only supports"):
        build_dossier(TargetSpec("Different Company", "different.example"), fixture=True)


@pytest.mark.parametrize("domain", ["", "example", "https://example.com", "example..com", "-bad.example"])
def test_target_spec_rejects_invalid_domains(domain):
    with pytest.raises(ValueError):
        TargetSpec("Example Co", domain)


def test_evidence_quotes_are_cited_in_markdown():
    dossier = build_dossier(fixture=True)
    markdown = render_markdown(dossier)
    for claim in dossier.claims:
        assert claim.source_url in markdown
        assert claim.retrieved_at in markdown


def test_fixture_dossier_output_contains_no_em_dash():
    dossier = build_dossier(fixture=True)
    assert chr(0x2014) not in render_markdown(dossier)
