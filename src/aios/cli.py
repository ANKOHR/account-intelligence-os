"""Command-line interface for building, briefing, scoring, and exporting dossiers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .models import Claim, Dossier, TargetSpec
from .pipeline import build_dossier
from .render import render_brief, render_json, render_markdown
from .scoring import score_opportunities


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aios", description="Build provenance-first account dossiers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="collect evidence and build a dossier")
    build.add_argument("--company", help="target company name")
    build.add_argument("--domain", help="target hostname")
    build.add_argument("--sector", default="", help="operator-provided sector hint")
    build.add_argument("--size-hint", default="", help="operator-provided size hint")
    build.add_argument("--github-org", default="", help="explicit public GitHub organization slug")
    build.add_argument("--fixture", action="store_true", help="use the bundled fictional company offline")
    build.add_argument("--output-dir", default="output", help="directory for dossier.md and dossier.json")

    brief = subparsers.add_parser("brief", help="print the call briefing from a dossier JSON file")
    brief.add_argument("dossier_json", type=Path)

    score = subparsers.add_parser("score", help="recompute and print opportunity scores")
    score.add_argument("dossier_json", type=Path, nargs="?")
    score.add_argument("--fixture", action="store_true", help="score the bundled fictional fixture")

    export = subparsers.add_parser("export", help="write a dossier as Markdown or JSON to stdout")
    export.add_argument("dossier_json", type=Path, nargs="?")
    export.add_argument("--format", choices=("md", "json"), required=True)
    export.add_argument("--fixture", action="store_true", help="export the bundled fictional fixture")
    return parser


def _load_dossier(path: Path) -> Dossier:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read dossier JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("dossier JSON must contain an object")
    return Dossier.from_dict(data)


def _fixture_or_file(path: Path | None, fixture: bool) -> Dossier:
    if path is not None:
        return _load_dossier(path)
    return build_dossier(fixture=True)


def _target_from_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> TargetSpec | None:
    if args.fixture and not args.company and not args.domain:
        return None
    if not args.company or not args.domain:
        parser.error("--company and --domain are required unless --fixture supplies its bundled target")
    try:
        return TargetSpec(args.company, args.domain, args.sector, args.size_hint, args.github_org)
    except ValueError as exc:
        parser.error(str(exc))
    return None


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            target = _target_from_args(args, parser)
            dossier = build_dossier(target=target, fixture=args.fixture)
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            md_path = output_dir / "dossier.md"
            json_path = output_dir / "dossier.json"
            md_path.write_text(render_markdown(dossier), encoding="utf-8")
            json_path.write_text(render_json(dossier) + "\n", encoding="utf-8")
            print(f"Wrote {md_path} and {json_path}")
            return 0

        if args.command == "brief":
            print(render_brief(_load_dossier(args.dossier_json)), end="")
            return 0

        if args.command == "score":
            dossier = _fixture_or_file(args.dossier_json, args.fixture)
            opportunities = score_opportunities(dossier.claims)
            print(json.dumps([item.to_dict() for item in opportunities], indent=2, ensure_ascii=False))
            return 0

        if args.command == "export":
            dossier = _fixture_or_file(args.dossier_json, args.fixture)
            output = render_markdown(dossier) if args.format == "md" else render_json(dossier)
            print(output, end="" if output.endswith("\n") else "\n")
            return 0
    except (ValueError, OSError) as exc:
        print(f"aios: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
