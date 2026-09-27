"""Validated data records used throughout the pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import re
from typing import Any
from urllib.parse import urlparse


def _clean_text(value: str) -> str:
    return " ".join(value.replace(chr(0x2014), ",").split())


class ProvenanceError(ValueError):
    """Raised when a factual claim does not have usable provenance."""


@dataclass(frozen=True)
class TargetSpec:
    company: str
    domain: str
    sector: str = ""
    size_hint: str = ""
    github_org: str = ""

    def __post_init__(self) -> None:
        company = _clean_text(self.company)
        domain = _clean_text(self.domain).rstrip(".")
        if not company:
            raise ValueError("company name must not be empty")
        if not domain:
            raise ValueError("domain must not be empty")
        if any(character in domain for character in ":/?#@"):
            raise ValueError("domain must be a hostname, for example example.com")
        try:
            ascii_domain = domain.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("domain must be a valid hostname") from exc
        label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        if len(ascii_domain) > 253 or not re.fullmatch(rf"{label}(?:\.{label})+", ascii_domain):
            raise ValueError("domain must be a valid hostname with at least two labels")
        object.__setattr__(self, "company", company)
        object.__setattr__(self, "domain", ascii_domain.lower())
        object.__setattr__(self, "sector", _clean_text(self.sector))
        object.__setattr__(self, "size_hint", _clean_text(self.size_hint))
        object.__setattr__(self, "github_org", _clean_text(self.github_org))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetSpec":
        return cls(
            company=str(data.get("company", "")),
            domain=str(data.get("domain", "")),
            sector=str(data.get("sector", "")),
            size_hint=str(data.get("size_hint", "")),
            github_org=str(data.get("github_org", "")),
        )


@dataclass(frozen=True)
class EvidenceRecord:
    source_url: str
    retrieved_at: str
    snippet: str
    source_kind: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_url", _clean_text(self.source_url))
        object.__setattr__(self, "retrieved_at", _clean_text(self.retrieved_at))
        object.__setattr__(self, "snippet", _clean_text(self.snippet))
        object.__setattr__(self, "source_kind", _clean_text(self.source_kind))

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    statement: str
    source_url: str
    retrieved_at: str
    supporting_quote: str
    source_kind: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _clean_text(self.claim_id))
        object.__setattr__(self, "statement", _clean_text(self.statement))
        object.__setattr__(self, "source_url", _clean_text(self.source_url))
        object.__setattr__(self, "retrieved_at", _clean_text(self.retrieved_at))
        object.__setattr__(self, "supporting_quote", _clean_text(self.supporting_quote))
        object.__setattr__(self, "source_kind", _clean_text(self.source_kind))
        if not self.statement.strip():
            raise ProvenanceError("claim statement must not be empty")
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ProvenanceError("claim source_url must be an absolute HTTP URL")
        try:
            date.fromisoformat(self.retrieved_at)
        except (TypeError, ValueError) as exc:
            raise ProvenanceError("claim retrieved_at must be an ISO date") from exc
        if not self.supporting_quote.strip():
            raise ProvenanceError("claim supporting_quote must not be empty")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Claim":
        return cls(
            claim_id=str(data.get("claim_id", "")),
            statement=str(data.get("statement", "")),
            source_url=str(data.get("source_url", "")),
            retrieved_at=str(data.get("retrieved_at", "")),
            supporting_quote=str(data.get("supporting_quote", "")),
            source_kind=str(data.get("source_kind", "")),
        )


@dataclass(frozen=True)
class AdapterResult:
    records: tuple[EvidenceRecord, ...] = ()
    unavailable: tuple[str, ...] = ()


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    service: str
    hypothesis: str
    score: int
    effort_proxy: str
    evidence_ids: tuple[str, ...]
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence_ids"] = list(self.evidence_ids)
        result["rationale"] = list(self.rationale)
        return result


@dataclass
class Dossier:
    target: dict[str, str]
    fixture_notice: str
    claims: list[Claim]
    source_status: list[str]
    opportunities: list[Opportunity]
    sections: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fixture_notice": self.fixture_notice,
            "target": dict(self.target),
            "source_status": list(self.source_status),
            "claims": [claim.to_dict() for claim in self.claims],
            "opportunities": [item.to_dict() for item in self.opportunities],
            "sections": self.sections,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dossier":
        claims = [Claim.from_dict(item) for item in data.get("claims", [])]
        opportunities = [
            Opportunity(
                opportunity_id=str(item["opportunity_id"]),
                service=str(item["service"]),
                hypothesis=str(item["hypothesis"]),
                score=int(item["score"]),
                effort_proxy=str(item["effort_proxy"]),
                evidence_ids=tuple(str(value) for value in item.get("evidence_ids", [])),
                rationale=tuple(str(value) for value in item.get("rationale", [])),
            )
            for item in data.get("opportunities", [])
        ]
        return cls(
            target={str(key): str(value) for key, value in data.get("target", {}).items()},
            fixture_notice=str(data.get("fixture_notice", "")),
            claims=claims,
            source_status=[str(item) for item in data.get("source_status", [])],
            opportunities=opportunities,
            sections=dict(data.get("sections", {})),
            schema_version=str(data.get("schema_version", "1")),
        )
