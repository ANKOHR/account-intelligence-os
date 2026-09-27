# Account Intelligence OS

Account Intelligence OS builds repeatable, evidence-led account dossiers. Each source-backed claim carries a URL, retrieval date, and supporting quote. Operator inputs are identified as unverified, missing data is marked unknown, and opportunity rankings use deterministic rules.

## Quickstart

Requirements: Python 3.10 or later. Runtime code uses only the Python standard library. Pytest is used for development checks.

From the repository directory in PowerShell:

```powershell
python -m pip install -e .
python -m aios build --fixture
```

The fixture build writes `output/dossier.md` and `output/dossier.json`. It performs no network requests. The generated dossier starts with a fictional fixture notice.

Build a live dossier by supplying a company and hostname:

```powershell
python -m aios build --company "Example Company" --domain example.com --sector "Financial software" --size-hint "Unknown"
```

Live collection requests the homepage, `/about`, `/news`, and `/careers`. GitHub collection is only attempted when an organization slug is explicitly configured:

```powershell
python -m aios build --company "Example Company" --domain example.com --github-org example-org
```

The package also installs the `aios` console command. If Python's Scripts directory is not on PATH, use `python -m aios` as shown here. Use `--output-dir PATH` to choose a different output directory. Sector, size, and target fields are operator-provided inputs, not verified claims.

Other commands:

```powershell
python -m aios brief output/dossier.json
python -m aios score output/dossier.json
python -m aios score --fixture
python -m aios export output/dossier.json --format md
python -m aios export output/dossier.json --format json
python -m aios export --format md --fixture
```

When `score` or `export` receives no dossier path, it uses the bundled fictional fixture. The output always labels fixture content clearly.

Run the tests with:

```powershell
python -m pytest -q
```

## Architecture

The pipeline follows a small set of explicit stages:

1. `TargetSpec` validates the required company name and hostname. Optional sector, size, and GitHub organization values remain marked as operator inputs.
2. Injectable source adapters fetch HTML pages and explicitly configured GitHub organization data. Parsing helpers convert HTML, news JSON, and GitHub JSON into evidence records. Each record has a source URL, retrieval date, source kind, and snippet. A new adapter can implement the `EvidenceAdapter` protocol and be supplied to the live collector.
3. The claim extractor assigns stable content-derived IDs and validates provenance. Records without an absolute HTTP URL, ISO retrieval date, statement, or supporting quote cannot become claims.
4. Rule-based scoring matches cited claims to automation, integrations, document pipelines, evaluation and observability tooling, and rapid prototypes. Each opportunity records fit, evidence strength, timing, an effort proxy, rationale, and evidence IDs. Equal scores use stable lexical tie-breaks.
5. The dossier assembler builds the profile, developments, technology signals, hypotheses, ranked opportunities, outreach angle, call briefing, objection prompts, follow-up ideas, and unknowns.
6. Renderers export the same structured dossier as Markdown or JSON.

The main modules are `src/aios/adapters.py`, `claims.py`, `scoring.py`, `pipeline.py`, `render.py`, and `cli.py`. Fixture files live under `fixtures/` and go through the same parsing functions used by source adapters.

## Honesty and provenance rules

- Every source-backed finding includes its source URL and retrieval date. The supporting quote is retained in JSON and in the Markdown evidence section.
- The Markdown renderer repeats citations beside the profile, development, technology, opportunity, and outreach statements that use the claim.
- Opportunity statements and pain points are hypotheses, not statements of verified need. They include the evidence that caused the rule to match.
- A script reference is reported as a markup reference. It is not presented as proof that a technology is active in production.
- Revenue, headcount, customer list, and decision makers are marked unknown unless evidence is collected. No values are inferred for them.
- A sector or size value supplied on the command line is labeled as unverified operator input.
- A source failure is listed as unavailable. It does not create a company claim.
- GitHub organization lookup requires `--github-org`. The program does not guess an organization from the company name.

## Fixture documentation

The bundled target, Northstar Ledger, is fictional. Its `.example` hostname, company pages, news item, careers page, and GitHub metadata are invented demo data. The dossier, call briefing, Markdown export, and JSON export all preserve the fictional notice. Fixture mode reads local files only and uses the HTML and JSON parsers directly, so the complete pipeline can run offline.

The fixture retrieval date is fixed at `2026-09-27` to make claims and opportunity rankings repeatable. It includes invoice workflow pages, a dated reconciliation assistant pilot, an Integration Engineer hiring signal, public repository metadata, and literal page asset references. None of these describe a real business.

## Scoring details

Only services with at least one matched source-backed claim are ranked. The integer score is:

`service fit + evidence strength + timing signal - effort adjustment`, clamped to `0..100`.

Evidence strength starts at 25 and adds 8 for each additional source category, capped at 45. A matched hiring or activity signal adds 15 timing points. Service fit and effort adjustments are fixed by the rules in `scoring.py`. The scorer sorts by descending score, then service name and opportunity ID. It uses no model calls or randomness.

## Current source limits

Live website collection checks a small set of conventional paths. It does not search the web, crawl arbitrary site maps, or claim that an empty page proves no activity exists. News JSON parsing is available for feeds and fixtures; live news collection currently reads the target's `/news` page as HTML. GitHub lookup requires an explicit organization slug. Missing or inaccessible sources remain unknown or unavailable.
