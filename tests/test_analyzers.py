"""Tests for the built-in analyzers, run directly (not through the registry).

The fixture verse below is original text written for this test suite. Its
rhymes were deliberately engineered and then confirmed against real
CMUdict pronunciations before being asserted here.
"""

from __future__ import annotations

from verseflow.analyzers.end_rhyme import EndRhymeAnalyzer
from verseflow.analyzers.flow_pattern import FlowPatternAnalyzer
from verseflow.analyzers.internal_rhyme import InternalRhymeAnalyzer
from verseflow.analyzers.syllables import SyllablesAnalyzer

FIXTURE_LINES = [
    "The night is bright with city light",
    "We chase the flow that feels so right",
    "A steady grind will clear the mind",
    "We leave the noise and doubt behind",
]


def test_syllables_analyzer_counts_are_correct() -> None:
    analyzer = SyllablesAnalyzer()
    result = analyzer.analyze(FIXTURE_LINES)

    assert result.analyzer == "syllables"
    per_line = [entry["syllables"] for entry in result.data["lines"]]
    assert per_line == [8, 8, 8, 8]
    assert result.data["total_syllables"] == 32
    assert "Total syllables: 32" in result.summary


def test_end_rhyme_analyzer_detects_aabb_scheme() -> None:
    analyzer = EndRhymeAnalyzer()
    result = analyzer.analyze(FIXTURE_LINES)

    assert result.data["scheme"] == "AABB"
    labels = [entry["label"] for entry in result.data["lines"]]
    assert labels == ["A", "A", "B", "B"]
    end_words = [entry["end_word"] for entry in result.data["lines"]]
    assert end_words == ["light", "right", "mind", "behind"]
    assert all(entry["rhyme_type"] == "exact" for entry in result.data["lines"])


def test_internal_rhyme_analyzer_finds_cross_line_chains() -> None:
    analyzer = InternalRhymeAnalyzer()
    result = analyzer.analyze(FIXTURE_LINES)

    chains_by_words = [
        frozenset(m["word"].lower() for m in c["words"]) for c in result.data["chains"]
    ]
    # "night", "bright", "light", and "right" all share the AY-T rhyme,
    # both as line-final words and as a mid-line word ("bright").
    assert frozenset({"night", "bright", "light", "right"}) in chains_by_words
    # "grind" (mid-line), "mind", and "behind" (both line-final) share AY-N-D.
    assert frozenset({"grind", "mind", "behind"}) in chains_by_words


def test_internal_rhyme_analyzer_ignores_repeated_identical_words() -> None:
    analyzer = InternalRhymeAnalyzer()
    lines = ["The flow the flow the flow", "goes on and on"]
    result = analyzer.analyze(lines)
    # Every chain candidate here would be the same word repeated -- none
    # of that counts as a "rhyme chain".
    assert result.data["chains"] == []


def test_flow_pattern_analyzer_produces_one_symbol_per_syllable() -> None:
    analyzer = FlowPatternAnalyzer()
    result = analyzer.analyze(FIXTURE_LINES)

    for entry in result.data["lines"]:
        assert set(entry["pattern_compact"]) <= {"x", "-"}
        assert len(entry["pattern_compact"]) == entry["syllables"]
    assert result.data["lines"][0]["syllables"] == 8


def test_analyzer_name_attributes_are_set() -> None:
    assert SyllablesAnalyzer().name == "syllables"
    assert EndRhymeAnalyzer().name == "end_rhyme"
    assert InternalRhymeAnalyzer().name == "internal_rhyme"
    assert FlowPatternAnalyzer().name == "flow_pattern"
