"""Markdown and JSON rendering for structured account dossiers."""

from __future__ import annotations

import json
from typing import Any

from .models import Dossier


def render_json(dossier: Dossier, indent: int = 2) -> str:
    return json.dumps(dossier.to_dict(), ensure_ascii=False, indent=indent, sort_keys=False)


def _claim_map(dossier: Dossier) -> dict[str, Any]:
    return {claim.claim_id: claim for claim in dossier.claims}


def _refs(ids: list[str] | tuple[str, ...], claims: dict[str, Any]) -> str:
    citations = []
    for claim_id in ids:
        claim = claims.get(claim_id)
        if claim:
            citations.append(f"[source]({claim.source_url}), retrieved {claim.retrieved_at}")
    return "; ".join(citations)


def render_markdown(dossier: Dossier) -> str:
    sections = dossier.sections
    claims = _claim_map(dossier)
    lines: list[str] = []
    if dossier.fixture_notice:
        lines.extend([f"> **{dossier.fixture_notice}**", ""])
    lines.extend([
        f"# Account dossier: {dossier.target.get('company', 'Unknown target')}",
        "",
        "## Target specification",
        "",
        f"- Company: {dossier.target.get('company', 'unknown')}",
        f"- Domain: {dossier.target.get('domain', 'unknown')}",
        f"- Sector: {dossier.target.get('sector', 'unknown')}",
        f"- Size hint: {dossier.target.get('size_hint', 'unknown')}",
        f"- GitHub organization: {dossier.target.get('github_org', 'unknown')}",
        f"- Status: {dossier.target.get('input_status', 'unknown')}",
        "",
        "All target fields above are inputs, not independently verified company facts.",
        "",
        "## Company profile",
        "",
    ])
    profile_ids = sections.get("profile", {}).get("claim_ids", [])
    if profile_ids:
        for claim_id in profile_ids:
            claim = claims.get(claim_id)
            if claim:
                lines.append(f"- {claim.statement} ({_refs([claim_id], claims)})")
    else:
        lines.append("- Company profile: unknown, no source-backed profile evidence was collected.")

    lines.extend(["", "## Recent developments", ""])
    news_ids = sections.get("recent_developments", {}).get("claim_ids", [])
    if news_ids:
        for claim_id in news_ids:
            claim = claims.get(claim_id)
            if claim:
                lines.append(f"- {claim.statement} ({_refs([claim_id], claims)})")
    else:
        lines.append("- Recent developments: unknown, no source-backed news evidence was collected.")

    lines.extend(["", "## Tech stack signals", ""])
    tech_ids = sections.get("tech_stack", {}).get("claim_ids", [])
    if tech_ids:
        for claim_id in tech_ids:
            claim = claims.get(claim_id)
            if claim:
                lines.append(f"- {claim.statement} ({_refs([claim_id], claims)})")
        lines.append(f"- {sections['tech_stack']['interpretation_note']}")
    else:
        lines.append("- Tech stack: unknown, no source-backed technology signals were collected.")

    lines.extend(["", "## Probable pain points", "", "Hypotheses only. Validate each in discovery.", ""])
    pain_items = sections.get("probable_pain_points", {}).get("items", [])
    if pain_items:
        for item in pain_items:
            lines.append(f"- **{item['service']} hypothesis:** {item['hypothesis']} ({_refs(item['evidence_ids'], claims)})")
    else:
        lines.append("- Unknown, there is not enough source-backed evidence to form a hypothesis.")

    lines.extend(["", "## Ranked opportunities", ""])
    if dossier.opportunities:
        for index, item in enumerate(dossier.opportunities, start=1):
            lines.extend([
                f"{index}. **{item.service}, {item.score}/100**. {item.hypothesis}",
                f"   Evidence: {_refs(item.evidence_ids, claims)}",
                f"   Effort proxy: {item.effort_proxy}.",
                f"   Rationale: {' '.join(item.rationale)}",
            ])
    else:
        lines.append("- No evidence-backed opportunities scored.")

    outreach = sections.get("outreach_angle", {})
    lines.extend(["", "## Outreach angle", "", f"{outreach.get('hook', 'Unknown')} {_refs(outreach.get('evidence_ids', []), claims)}", ""])

    briefing = sections.get("call_briefing", {})
    lines.extend(["## Call briefing", "", f"- Opening: {briefing.get('opening', 'Unknown')} {_refs(briefing.get('opening_evidence_ids', []), claims)}", f"- Goal: {briefing.get('goal', 'Unknown')}", "", "Questions:"])
    for item in briefing.get("questions", []):
        suffix = _refs(item.get("evidence_ids", []), claims)
        lines.append(f"- {item.get('question', '')} {suffix}".rstrip())

    lines.extend(["", "## Objection prep", ""])
    objections = sections.get("objection_prep", [])
    if objections:
        for item in objections:
            lines.append(f"- Possible objection: {item['possible_objection']} Suggested response: {item['response_idea']} ({_refs(item['evidence_ids'], claims)})")
    else:
        lines.append("- No evidence-backed objection prompts available.")

    lines.extend(["", "## Follow-up ideas", ""])
    follow_ups = sections.get("follow_up_ideas", [])
    if follow_ups:
        for item in follow_ups:
            lines.append(f"- If useful in discovery: {item['trigger']} Next step: {item['idea']} ({_refs(item['evidence_ids'], claims)})")
    else:
        lines.append("- Unknown, no evidence-backed follow-up idea is available.")

    lines.extend(["", "## Unknowns", ""])
    for item in sections.get("unknowns", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Evidence-backed findings", ""])
    if dossier.claims:
        for claim in dossier.claims:
            lines.append(f"- **{claim.claim_id}:** {claim.statement} Supporting quote: `{claim.supporting_quote}`. Citation: {_refs([claim.claim_id], claims)}.")
    else:
        lines.append("- No claims passed provenance validation.")

    lines.extend(["", "## Source coverage", ""])
    if dossier.source_status:
        for status in dossier.source_status:
            lines.append(f"- {status}")
    else:
        lines.append("- No source adapters reported an unavailable source.")
    return "\n".join(lines).rstrip() + "\n"


def render_brief(dossier: Dossier) -> str:
    claims = _claim_map(dossier)
    briefing = dossier.sections.get("call_briefing", {})
    lines = [f"Call briefing: {dossier.target.get('company', 'unknown')}", ""]
    if dossier.fixture_notice:
        lines.extend([dossier.fixture_notice, ""])
    opening_refs = _refs(briefing.get("opening_evidence_ids", []), claims)
    lines.extend([f"Opening: {briefing.get('opening', 'Unknown')} {opening_refs}".rstrip(), f"Goal: {briefing.get('goal', 'Unknown')}", "", "Questions:"])
    for item in briefing.get("questions", []):
        citations = _refs(item.get("evidence_ids", []), claims)
        lines.append(f"- {item.get('question', '')} {citations}".rstrip())
    lines.extend(["", "Objection prompts:"])
    for item in dossier.sections.get("objection_prep", []):
        citations = _refs(item.get("evidence_ids", []), claims)
        lines.append(f"- {item['possible_objection']} Response idea: {item['response_idea']} ({citations})")
    return "\n".join(lines).rstrip() + "\n"
