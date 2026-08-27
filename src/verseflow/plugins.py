"""The analyzer plugin registry.

This is the piece that makes verseflow's analysis pipeline genuinely
extensible: built-in analyzers (``syllables``, ``end_rhyme``,
``internal_rhyme``, ``flow_pattern``) are not special-cased anywhere --
they are registered exactly the same way a third-party package would
register its own analyzer, through the ``verseflow.analyzers`` Python
entry-point group declared in ``pyproject.toml``:

.. code-block:: toml

    [project.entry-points."verseflow.analyzers"]
    syllables = "verseflow.analyzers.syllables:get_analyzer"
    end_rhyme = "verseflow.analyzers.end_rhyme:get_analyzer"
    internal_rhyme = "verseflow.analyzers.internal_rhyme:get_analyzer"
    flow_pattern = "verseflow.analyzers.flow_pattern:get_analyzer"

A third-party package can add its own analyzer by declaring the same
entry-point group in *its own* ``pyproject.toml`` -- see
``CONTRIBUTING.md`` for a full worked example. Once that package is
`pip install`-ed alongside verseflow, :func:`list_analyzers` and
:func:`run_pipeline` will pick it up automatically, with no changes to
verseflow's own source required.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any

from verseflow.analyzers import AnalysisResult, Analyzer

ENTRY_POINT_GROUP = "verseflow.analyzers"


class AnalyzerRegistry:
    """Holds the set of analyzers available to the pipeline.

    Analyzers reach the registry two ways:

    1. **Entry points** -- discovered lazily from the ``verseflow.analyzers``
       group the first time the registry is used (see :meth:`discover`).
    2. **Direct registration** -- :meth:`register`, for programmatic use
       (tests, notebooks, or a host application embedding verseflow
       without going through packaging metadata at all).
    """

    def __init__(self) -> None:
        self._analyzers: dict[str, Analyzer] = {}
        self._discovered = False

    def register(self, analyzer: Analyzer, *, override: bool = False) -> None:
        """Register an analyzer instance under its ``.name``.

        Raises ``ValueError`` if an analyzer with the same name is already
        registered, unless ``override=True``.
        """
        if not analyzer.name:
            raise ValueError(f"{type(analyzer).__name__} does not set a non-empty `name`")
        if analyzer.name in self._analyzers and not override:
            raise ValueError(
                f"an analyzer named {analyzer.name!r} is already registered "
                f"({type(self._analyzers[analyzer.name]).__name__}); pass "
                f"override=True to replace it"
            )
        self._analyzers[analyzer.name] = analyzer

    def discover(self, *, force: bool = False) -> list[str]:
        """Discover and register analyzers from the ``verseflow.analyzers`` entry-point group.

        Idempotent: subsequent calls are no-ops unless ``force=True``.
        A plugin that fails to import or return a valid :class:`Analyzer`
        is skipped with a warning rather than crashing the whole
        pipeline -- one broken third-party plugin should never take down
        analysis for everyone else.

        Returns the list of newly-registered analyzer names.
        """
        if self._discovered and not force:
            return []

        newly_registered = []
        eps = entry_points(group=ENTRY_POINT_GROUP)
        for ep in eps:
            try:
                loaded = ep.load()
                analyzer = loaded() if isinstance(loaded, type) else loaded
                if callable(analyzer) and not isinstance(analyzer, Analyzer):
                    # Support plain factory functions/callables that return
                    # an Analyzer instance when called with no arguments,
                    # in addition to classes and ready-made instances.
                    analyzer = analyzer()
                if not isinstance(analyzer, Analyzer):
                    raise TypeError(
                        f"entry point {ep.name!r} did not produce an Analyzer instance "
                        f"(got {type(analyzer).__name__})"
                    )
            except Exception as exc:  # noqa: BLE001 - intentionally broad: isolate bad plugins
                import warnings

                warnings.warn(
                    f"skipping verseflow analyzer plugin {ep.name!r}: {exc}",
                    stacklevel=2,
                )
                continue

            self.register(analyzer, override=True)
            newly_registered.append(analyzer.name)

        self._discovered = True
        return newly_registered

    def get(self, name: str) -> Analyzer:
        """Look up a registered analyzer by name, discovering plugins first if needed."""
        self.discover()
        try:
            return self._analyzers[name]
        except KeyError:
            available = ", ".join(sorted(self._analyzers)) or "(none)"
            raise KeyError(
                f"no analyzer named {name!r} is registered. Available: {available}"
            ) from None

    def names(self) -> list[str]:
        """Return the sorted names of all registered analyzers, discovering plugins first."""
        self.discover()
        return sorted(self._analyzers)

    def all(self) -> list[Analyzer]:
        """Return all registered analyzer instances, discovering plugins first."""
        self.discover()
        return [self._analyzers[name] for name in sorted(self._analyzers)]


class PipelineResult:
    """The combined output of running one or more analyzers over a text."""

    def __init__(self, lines: list[str], results: dict[str, AnalysisResult]) -> None:
        self.lines = lines
        self.results = results

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the whole pipeline run."""
        return {
            "lines": self.lines,
            "analyzers": {
                name: {"summary": result.summary, "data": result.data}
                for name, result in self.results.items()
            },
        }

    def __getitem__(self, analyzer_name: str) -> AnalysisResult:
        return self.results[analyzer_name]

    def __contains__(self, analyzer_name: str) -> bool:
        return analyzer_name in self.results

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"PipelineResult(lines={len(self.lines)}, analyzers={list(self.results)})"


# A single process-wide registry, in the same spirit as, e.g.,
# ``logging``'s module-level default logger. Most callers should just use
# the module-level functions below; :class:`AnalyzerRegistry` itself stays
# available for tests or callers that want an isolated registry.
_default_registry = AnalyzerRegistry()


def register_analyzer(analyzer: Analyzer, *, override: bool = False) -> None:
    """Register ``analyzer`` on the default, process-wide registry."""
    _default_registry.register(analyzer, override=override)


def get_analyzer(name: str) -> Analyzer:
    """Fetch an analyzer by name from the default registry."""
    return _default_registry.get(name)


def list_analyzers() -> list[str]:
    """List every analyzer name known to the default registry (built-in + plugins)."""
    return _default_registry.names()


def run_pipeline(text: str, analyzer_names: list[str] | None = None) -> PipelineResult:
    """Run one or more analyzers over ``text`` and merge their results.

    Args:
        text: Raw lyric/poem text. Split into lines on newlines; blank
            (whitespace-only) lines are dropped before analysis, so
            stanza breaks in the input don't skew line numbering.
        analyzer_names: Which analyzers to run, by name. ``None`` (the
            default) runs every analyzer currently registered, built-in
            and third-party alike.

    Returns:
        A :class:`PipelineResult` with one :class:`~verseflow.analyzers.AnalysisResult`
        per requested analyzer, keyed by analyzer name.

    An analyzer that raises an exception does not abort the whole
    pipeline: its failure is captured as a result with an ``"error"`` key
    in ``data`` instead, so a single misbehaving plugin can't take down
    analysis of the other passes.
    """
    lines = [line for line in text.splitlines() if line.strip()]
    names = analyzer_names if analyzer_names is not None else list_analyzers()

    results: dict[str, AnalysisResult] = {}
    for name in names:
        analyzer = get_analyzer(name)
        try:
            results[name] = analyzer.analyze(lines)
        except Exception as exc:  # noqa: BLE001 - intentionally broad: isolate bad plugins
            results[name] = AnalysisResult(
                analyzer=name,
                summary=f"[{name}] analysis failed: {exc}",
                data={"error": str(exc)},
            )

    return PipelineResult(lines=lines, results=results)
