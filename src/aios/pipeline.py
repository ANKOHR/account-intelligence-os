"""End-to-end evidence collection, analysis, scoring, and dossier assembly."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .adapters import collect_live_evidence
from .claims import extract_claims
from .fixtures import fixture_target, load_fixture_evidence
from .models import Dossier, TargetSpec
from .scoring import score_opportunities


FIXTURE_NOTICE = (
    "FICTIONAL FIXTURE: Northstar Ledger, its sources, and all evidence in this dossier "
    "are invented for offline demonstration. Do not treat them as real."
)


def _target_dict(target: TargetSpec, fixture: bool) -> dict[str, str]:
    return {
        "company": target.company,
        "domain": target.domain,
        "sector": target.sector or "unknown",
        "size_hint": target.size_hint or "unknown",
        "github_org": target.github_org or "unknown",
        "input_status": "Fixture target" if fixture else "Operator input, not independently verified",
    }


def _first_match(opportunities: list[Any], prefix: str) -> Any | None:
    return next((item for item in opportunities if item.opportunity_id.startswith(prefix)), None)


def assemble_sections(claims: list[Any], opportunities: list[Any], source_status: list[str]) -> dict[str, Any]:
    by_kind: dict[str, list[str]] = {}
    statement_by_id: dict[str, str] = {}
    for claim in claims:
        kind = claim.source_kind.split(":", 1)[0]
        by_kind.setdefault(kind, []).append(claim.claim_id)
        statement_by_id[claim.claim_id] = claim.statement

    evidence_by_service = {item.opportunity_id: list(item.evidence_ids) for item in opportunities}
    pain_hypotheses = [
        {"hypothesis": item.hypothesis, "service": item.service, "evidence_ids": list(item.evidence_ids)}
        for item in opportunities[:4]
    ]

    news_claims = by_kind.get("news", [])
    best_news = news_claims[0] if news_claims else ""
    if best_news:
        hook_text = (
            f"Open by referencing this reported development: {statement_by_id[best_news]} "
            "Ask what it is meant to validate and where implementation support would be useful."
        )
        hook_ids = [best_news]
    elif opportunities:
        first = opportunities[0]
        hook_text = f"Open with the source-backed signal relevant to {first.service.lower()}, then ask what would make a small next step valuable."
        hook_ids = list(first.evidence_ids)
    else:
        hook_text = "No evidence-backed outreach hook is available yet. Ask for a referral to the person responsible for the target workflow."
        hook_ids = []

    integration = _first_match(opportunities, "integrations")
    documents = _first_match(opportunities, "document_pipelines")
    evaluation = _first_match(opportunities, "eval_observability")
    call_questions: list[dict[str, Any]] = []
    if documents:
        call_questions.append({
            "question": "What steps happen between document intake and approval, and where do exceptions go?",
            "evidence_ids": evidence_by_service[documents.opportunity_id],
        })
    if integration:
        call_questions.append({
            "question": "Which systems need to stay in sync, and where does connector work currently take effort?",
            "evidence_ids": evidence_by_service[integration.opportunity_id],
        })
    if evaluation:
        call_questions.append({
            "question": "What checks would make the cited assistant workflow safe and useful to expand?",
            "evidence_ids": evidence_by_service[evaluation.opportunity_id],
        })
    if not call_questions:
        call_questions.append({"question": "Which operational workflow is most useful to discuss first?", "evidence_ids": []})

    objection_prep = [
        {
            "possible_objection": f"We already have {item.service.lower()} covered.",
            "response_idea": "Acknowledge that, then ask whether a small, bounded review of the cited workflow would surface any uncovered edge cases.",
            "evidence_ids": list(item.evidence_ids),
        }
        for item in opportunities[:3]
    ]
    follow_up_ideas = [
        {
            "trigger": item.hypothesis,
            "idea": f"Offer a short, scoped discovery note outlining a first step for {item.service.lower()}.",
            "evidence_ids": list(item.evidence_ids),
        }
        for item in opportunities[:3]
    ]

    return {
        "profile": {
            "claim_ids": by_kind.get("company_site", []),
            "input_note": "Target fields are operator-provided inputs and are not independently verified.",
        },
        "recent_developments": {"claim_ids": news_claims},
        "tech_stack": {
            "claim_ids": by_kind.get("tech_signal", []) + by_kind.get("github", []),
            "interpretation_note": "These are literal HTML references and do not prove a technology is active in production.",
        },
        "probable_pain_points": {"label": "Hypotheses only, validate in discovery", "items": pain_hypotheses},
        "outreach_angle": {"hook": hook_text, "evidence_ids": hook_ids},
        "call_briefing": {
            "opening": hook_text,
            "opening_evidence_ids": hook_ids,
            "goal": "Confirm the relevant workflow, owner, constraints, and a measurable next step.",
            "questions": call_questions,
        },
        "objection_prep": objection_prep,
        "follow_up_ideas": follow_up_ideas,
        "unknowns": [
            "Revenue: unknown",
            "Headcount: unknown",
            "Customer list: unknown",
            "Decision makers: unknown",
            *[f"Source: {item}" for item in source_status],
        ],
        "source_coverage": list(source_status),
    }


def build_dossier(target: TargetSpec | None = None, fixture: bool = False) -> Dossier:
    """Build a complete dossier. Fixture mode has no network-capable code path."""
    fixture_notice = ""
    if fixture:
        expected = fixture_target()
        if target is not None and (
            target.company.casefold() != expected.company.casefold()
            or target.domain.casefold() != expected.domain.casefold()
        ):
            raise ValueError("fixture mode only supports the bundled fictional Northstar Ledger target")
        if target is None:
            target = expected
        records, source_status = load_fixture_evidence()
        fixture_notice = FIXTURE_NOTICE
    else:
        if target is None:
            raise ValueError("a target specification is required outside fixture mode")
        retrieved_at = datetime.now(timezone.utc).date().isoformat()
        result = collect_live_evidence(target, retrieved_at)
        records = list(result.records)
        source_status = list(result.unavailable)

    claims = extract_claims(records)
    opportunities = score_opportunities(claims)
    sections = assemble_sections(claims, opportunities, source_status)
    return Dossier(
        target={
            "company": target.company,
            "domain": target.domain,
            "sector": target.sector or "unknown",
            "size_hint": target.size_hint or "unknown",
            "github_org": target.github_org or "unknown",
            "input_status": "Fixture target" if fixture else "Operator input, not independently verified",
        },
        fixture_notice=fixture_notice,
        claims=claims,
        source_status=source_status,
        opportunities=opportunities,
        sections=sections,
    )


def fixture_dossier_dict() -> dict[str, Any]:
    """Convenience entry point for consumers that need a plain JSON object."""
    return build_dossier(fixture=True).to_dict()
