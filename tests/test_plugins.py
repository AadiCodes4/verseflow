"""Tests for the plugin registry (verseflow.plugins).

These tests exercise the actual entry-point discovery mechanism: the
package under test is installed (``pip install -e .``), so
``importlib.metadata.entry_points(group="verseflow.analyzers")`` finds
the four built-in analyzers exactly the way it would find a third-party
plugin package's analyzers -- there is no special-casing of "built-in"
analyzers anywhere in the registry.
"""

from __future__ import annotations

import pytest

from verseflow.analyzers import AnalysisResult, Analyzer
from verseflow.plugins import (
    AnalyzerRegistry,
    get_analyzer,
    list_analyzers,
    register_analyzer,
    run_pipeline,
)

BUILTIN_NAMES = {"syllables", "end_rhyme", "internal_rhyme", "flow_pattern"}


class BrokenAnalyzer(Analyzer):
    """A deliberately misbehaving analyzer, used to test failure isolation."""

    name = "broken_test_analyzer"

    def analyze(self, lines: list[str]) -> AnalysisResult:
        raise RuntimeError("boom")


class UppercaseAnalyzer(Analyzer):
    """A trivial, well-behaved third-party-style analyzer for registry tests."""

    name = "uppercase_test_analyzer"

    def analyze(self, lines: list[str]) -> AnalysisResult:
        upper = [line.upper() for line in lines]
        return AnalysisResult(analyzer=self.name, summary="\n".join(upper), data={"lines": upper})


def test_entry_point_discovery_finds_all_builtin_analyzers() -> None:
    names = set(list_analyzers())
    assert BUILTIN_NAMES <= names


def test_get_analyzer_returns_instances_of_expected_classes() -> None:
    from verseflow.analyzers.end_rhyme import EndRhymeAnalyzer
    from verseflow.analyzers.flow_pattern import FlowPatternAnalyzer
    from verseflow.analyzers.internal_rhyme import InternalRhymeAnalyzer
    from verseflow.analyzers.syllables import SyllablesAnalyzer

    assert isinstance(get_analyzer("syllables"), SyllablesAnalyzer)
    assert isinstance(get_analyzer("end_rhyme"), EndRhymeAnalyzer)
    assert isinstance(get_analyzer("internal_rhyme"), InternalRhymeAnalyzer)
    assert isinstance(get_analyzer("flow_pattern"), FlowPatternAnalyzer)


def test_get_analyzer_missing_name_raises_helpful_error() -> None:
    with pytest.raises(KeyError, match="no analyzer named 'does_not_exist'"):
        get_analyzer("does_not_exist")


def test_register_analyzer_third_party_style() -> None:
    register_analyzer(UppercaseAnalyzer(), override=True)
    try:
        assert "uppercase_test_analyzer" in list_analyzers()
        analyzer = get_analyzer("uppercase_test_analyzer")
        result = analyzer.analyze(["hello world"])
        assert result.data["lines"] == ["HELLO WORLD"]
    finally:
        # Registries are process-global; keep this test from leaking into
        # others by not asserting further, and by using override=True so
        # re-running the suite (or other tests re-registering the same
        # name) never fails on a duplicate-registration error.
        pass


def test_isolated_registry_rejects_duplicate_names_without_override() -> None:
    registry = AnalyzerRegistry()
    registry.register(UppercaseAnalyzer())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(UppercaseAnalyzer())
    # override=True should succeed instead of raising.
    registry.register(UppercaseAnalyzer(), override=True)


def test_isolated_registry_requires_a_name() -> None:
    class Nameless(Analyzer):
        name = ""

        def analyze(self, lines: list[str]) -> AnalysisResult:
            return AnalysisResult(analyzer="", summary="", data={})

    registry = AnalyzerRegistry()
    with pytest.raises(ValueError, match="non-empty `name`"):
        registry.register(Nameless())


def test_run_pipeline_runs_all_analyzers_by_default() -> None:
    result = run_pipeline("cat in a hat\nsat right there")
    assert BUILTIN_NAMES <= set(result.results)
    assert result.lines == ["cat in a hat", "sat right there"]


def test_run_pipeline_respects_analyzer_name_subset() -> None:
    result = run_pipeline("cat in a hat\nsat right there", analyzer_names=["syllables"])
    assert set(result.results) == {"syllables"}


def test_run_pipeline_skips_blank_lines() -> None:
    result = run_pipeline("first line\n\n\nsecond line\n")
    assert result.lines == ["first line", "second line"]


def test_run_pipeline_isolates_a_broken_analyzer() -> None:
    register_analyzer(BrokenAnalyzer(), override=True)
    result = run_pipeline(
        "cat in a hat\nsat right there",
        analyzer_names=["syllables", "broken_test_analyzer"],
    )
    # The well-behaved analyzer still produced real output...
    assert result.results["syllables"].data["total_syllables"] > 0
    # ...and the broken one is captured as a failed result, not a crash.
    assert "error" in result.results["broken_test_analyzer"].data
    assert "boom" in result.results["broken_test_analyzer"].data["error"]


def test_pipeline_result_to_dict_round_trips_through_json() -> None:
    import json

    result = run_pipeline("cat in a hat\nsat right there", analyzer_names=["syllables"])
    payload = json.dumps(result.to_dict())
    reloaded = json.loads(payload)
    assert reloaded["lines"] == result.lines
    assert "syllables" in reloaded["analyzers"]
