"""Stable, rule-based scoring for evidence-backed Henry-relevant opportunities."""

from __future__ import annotations

import re

from .models import Claim, Opportunity


_RULES = (
    {
        "id": "automation",
        "service": "Workflow automation",
        "terms": re.compile(r"manual|reconciliation|mismatch|repetitive|spreadsheet|monthly close", re.I),
        "fit": 24,
        "effort": "medium",
        "penalty": 4,
        "hypothesis": "A focused automation may reduce repetitive handling around a cited workflow, if discovery confirms a suitable gap.",
    },
    {
        "id": "integrations",
        "service": "Integrations",
        "terms": re.compile(r"integration|connector|accounting tools|sync|api", re.I),
        "fit": 25,
        "effort": "medium",
        "penalty": 4,
        "hypothesis": "A connector or synchronization improvement may be useful, if discovery confirms an integration bottleneck.",
    },
    {
        "id": "document_pipelines",
        "service": "Document pipelines",
        "terms": re.compile(r"invoice|document|upload|approval|pdf|contract", re.I),
        "fit": 24,
        "effort": "medium",
        "penalty": 4,
        "hypothesis": "A document pipeline review may uncover a narrow routing or extraction improvement, if discovery confirms need.",
    },
    {
        "id": "eval_observability",
        "service": "Evaluation and observability tooling",
        "terms": re.compile(r"assistant|model|\bAI\b|evaluation|monitor|observability", re.I),
        "fit": 21,
        "effort": "high",
        "penalty": 7,
        "hypothesis": "Lightweight evaluation or monitoring may help assess a cited assistant or model workflow, if one is in scope.",
    },
    {
        "id": "rapid_prototypes",
        "service": "Rapid prototypes",
        "terms": re.compile(r"pilot|beta|launch|prototype|new product", re.I),
        "fit": 23,
        "effort": "low",
        "penalty": 1,
        "hypothesis": "A bounded prototype may help test the cited initiative, if the team wants external implementation support.",
    },
)

_TIMING = re.compile(r"pilot|hiring|career|role|announced|begins|launch|beta", re.I)


def score_opportunities(claims: list[Claim] | tuple[Claim, ...]) -> list[Opportunity]:
    """Score each supported service hypothesis with deterministic integer rules.

    Formula: fit (19 to 25) + evidence strength (25 per source category,
    capped at 45) + timing (15 when a matched claim signals activity) -
    effort penalty. Unsupported services are omitted. Stable lexical tie-breaks
    make equal scores reproducible.
    """
    scored: list[Opportunity] = []
    for rule in _RULES:
        matches = [claim for claim in claims if rule["terms"].search(claim.statement)]
        if not matches:
            continue
        categories = sorted({claim.source_kind.split(":", 1)[0] for claim in matches})
        strength = min(45, 25 + 8 * (len(categories) - 1))
        timing = 15 if any(_TIMING.search(claim.statement) for claim in matches) else 0
        score = max(0, min(100, int(rule["fit"]) + strength + timing - int(rule["penalty"])))
        rationale = (
            f"Service fit: {rule['fit']} points.",
            f"Evidence strength: {strength} points across {len(categories)} source category or categories.",
            f"Timing signal: {timing} points.",
            f"Effort proxy: {rule['effort']} with a {rule['penalty']} point adjustment.",
        )
        scored.append(
            Opportunity(
                opportunity_id=str(rule["id"]),
                service=str(rule["service"]),
                hypothesis=str(rule["hypothesis"]),
                score=score,
                effort_proxy=str(rule["effort"]),
                evidence_ids=tuple(sorted(claim.claim_id for claim in matches)),
                rationale=rationale,
            )
        )
    return sorted(scored, key=lambda item: (-item.score, item.service.casefold(), item.opportunity_id))
