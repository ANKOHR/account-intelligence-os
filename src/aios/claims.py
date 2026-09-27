"""Claim normalization with required URL, date, and supporting quote."""

from __future__ import annotations

import hashlib
import json

from .models import Claim, EvidenceRecord, ProvenanceError


def claim_from_evidence(record: EvidenceRecord) -> Claim:
    """Normalize one evidence record, rejecting absent or malformed provenance."""
    statement = record.snippet.strip()
    quote = record.snippet.strip()
    if record.source_kind == "github":
        try:
            repo = json.loads(record.snippet)
        except json.JSONDecodeError as exc:
            raise ValueError("GitHub evidence must contain valid repository JSON") from exc
        if not isinstance(repo, dict) or not repo.get("name"):
            raise ValueError("GitHub evidence is missing a repository name")
        language = repo.get("language") or "not reported"
        statement = f"GitHub public repository metadata lists {repo['name']} with primary language {language}."
    elif record.source_kind.startswith("tech_signal:"):
        technology = record.source_kind.split(":", 1)[1]
        statement = f"Page markup contains a reference matching {technology}: {record.snippet.strip()}."
        quote = record.snippet.strip()

    digest_input = "\n".join((record.source_url, record.retrieved_at, record.source_kind, quote))
    claim_id = "claim-" + hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:12]
    try:
        return Claim(
            claim_id=claim_id,
            statement=statement,
            source_url=record.source_url,
            retrieved_at=record.retrieved_at,
            supporting_quote=quote,
            source_kind=record.source_kind,
        )
    except ProvenanceError:
        raise


def extract_claims(records: list[EvidenceRecord] | tuple[EvidenceRecord, ...]) -> list[Claim]:
    """Normalize evidence deterministically and drop duplicate records."""
    normalized: dict[str, Claim] = {}
    for record in records:
        if not record.snippet.strip():
            continue
        claim = claim_from_evidence(record)
        normalized[claim.claim_id] = claim
    return [normalized[key] for key in sorted(normalized)]
