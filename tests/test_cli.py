"""Tests for the verseflow CLI (verseflow.cli)."""

from __future__ import annotations

import json

from verseflow.cli import DEMO_VERSE, main


def test_demo_verse_contains_no_placeholder_markers() -> None:
    # Sanity check that the shipped demo verse is real, non-empty text
    # (guards against an accidental empty-string regression).
    lines = [line for line in DEMO_VERSE.splitlines() if line.strip()]
    assert len(lines) == 8


def test_list_analyzers_command(capsys) -> None:
    exit_code = main(["list-analyzers"])
    captured = capsys.readouterr()
    assert exit_code == 0
    for name in ("syllables", "end_rhyme", "internal_rhyme", "flow_pattern"):
        assert name in captured.out


def test_demo_command_ascii_output(capsys) -> None:
    exit_code = main(["demo", "--format", "ascii"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "end_rhyme" in captured.out
    assert "Scheme:" in captured.out
    assert "internal_rhyme" in captured.out


def test_demo_command_json_output_is_valid_and_complete(capsys) -> None:
    exit_code = main(["demo", "--format", "json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert set(payload["analyzers"]) == {"syllables", "end_rhyme", "internal_rhyme", "flow_pattern"}
    assert payload["analyzers"]["end_rhyme"]["data"]["scheme"] == "AABBCCDD"


def test_demo_command_html_output_is_self_contained(capsys) -> None:
    exit_code = main(["demo", "--format", "html"])
    captured = capsys.readouterr()
    assert exit_code == 0
    html_out = captured.out
    assert "<html" in html_out
    assert "<script>" in html_out
    # No external CDN / stylesheet / script references anywhere.
    assert "http://" not in html_out
    assert "https://" not in html_out


def test_demo_command_analyzer_subset(capsys) -> None:
    exit_code = main(["demo", "--format", "json", "--analyzers", "syllables"])
    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert set(payload["analyzers"]) == {"syllables"}


def test_analyze_command_on_a_real_file(tmp_path, capsys) -> None:
    verse_file = tmp_path / "verse.txt"
    verse_file.write_text(
        "The night is bright with city light\nWe chase the flow that feels so right\n"
    )

    exit_code = main(["analyze", str(verse_file), "--format", "json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["analyzers"]["end_rhyme"]["data"]["scheme"] == "AA"


def test_analyze_command_missing_file_returns_error(capsys) -> None:
    exit_code = main(["analyze", "/no/such/file.txt"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "no such file" in captured.err


def test_analyze_command_writes_output_file(tmp_path) -> None:
    verse_file = tmp_path / "verse.txt"
    verse_file.write_text("cat in a hat\nsat right there\n")
    out_file = tmp_path / "report.html"

    exit_code = main(
        ["analyze", str(verse_file), "--format", "html", "-o", str(out_file)]
    )
    assert exit_code == 0
    assert out_file.exists()
    assert "<html" in out_file.read_text(encoding="utf-8")
