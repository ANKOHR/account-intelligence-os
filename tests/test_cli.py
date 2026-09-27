from __future__ import annotations

import json

from aios.cli import main


def test_cli_build_fixture_writes_markdown_and_json(tmp_path, capsys):
    out = tmp_path / "built"
    assert main(["build", "--fixture", "--output-dir", str(out)]) == 0
    assert "Wrote" in capsys.readouterr().out
    markdown = (out / "dossier.md").read_text(encoding="utf-8")
    data = json.loads((out / "dossier.json").read_text(encoding="utf-8"))
    assert markdown.startswith("> **FICTIONAL FIXTURE:")
    assert data["fixture_notice"].startswith("FICTIONAL FIXTURE:")


def test_cli_brief_reads_a_dossier(tmp_path, capsys):
    out = tmp_path / "built"
    assert main(["build", "--fixture", "--output-dir", str(out)]) == 0
    capsys.readouterr()
    assert main(["brief", str(out / "dossier.json")]) == 0
    assert "Call briefing:" in capsys.readouterr().out


def test_cli_score_fixture_runs(capsys):
    assert main(["score", "--fixture"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output
    assert output[0]["score"] >= output[-1]["score"]


def test_cli_export_markdown_fixture_runs(capsys):
    assert main(["export", "--format", "md", "--fixture"]) == 0
    assert "## Ranked opportunities" in capsys.readouterr().out


def test_cli_export_json_fixture_runs(capsys):
    assert main(["export", "--format", "json", "--fixture"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == "1"


def test_cli_score_and_export_use_a_saved_dossier(tmp_path, capsys):
    out = tmp_path / "built"
    assert main(["build", "--fixture", "--output-dir", str(out)]) == 0
    capsys.readouterr()
    saved = str(out / "dossier.json")
    assert main(["score", saved]) == 0
    assert json.loads(capsys.readouterr().out)
    assert main(["export", saved, "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["fixture_notice"]
