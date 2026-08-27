"""The verseflow analyzer plugin contract.

Every analysis pass in verseflow -- the four built-in ones and any
third-party ones registered via the ``verseflow.analyzers`` entry-point
group -- implements the :class:`Analyzer` ABC defined here and returns an
:class:`AnalysisResult`. This module intentionally has *no* dependency on
``verseflow.plugins`` (the registry) or ``verseflow.cli`` -- it only
defines the shape a plugin must have, so a third-party package can depend
on ``verseflow`` for this module alone without pulling in the CLI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    """The output of a single analyzer run over a set of lyric lines.

    Attributes:
        analyzer: The analyzer's registered name (e.g. ``"end_rhyme"``).
        summary: A human-readable, plain-text/ASCII rendering of the
            result, suitable for printing directly to a terminal.
        data: A JSON-serializable structured payload with the same
            information in machine-readable form, for the ``json`` and
            ``html`` output formats and for other analyzers/tools to
            consume.
    """

    analyzer: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)


class Analyzer(ABC):
    """Base class for a verseflow analysis pass.

    Subclasses must set :attr:`name` and implement :meth:`analyze`.
    An analyzer receives the lyric text as a list of non-blank lines
    (blank/whitespace-only lines used as stanza breaks are filtered out
    before analyzers ever see the text) and returns one
    :class:`AnalysisResult`.

    This is deliberately a small, stable surface: a third-party plugin
    package only needs to implement this one class and register it under
    the ``verseflow.analyzers`` entry-point group to plug into the full
    CLI, JSON export, and HTML report -- see ``CONTRIBUTING.md`` for a
    worked example.
    """

    #: Unique, stable identifier for this analyzer (used on the CLI via
    #: ``--analyzers`` and as the key in pipeline output).
    name: str = ""

    @abstractmethod
    def analyze(self, lines: list[str]) -> AnalysisResult:
        """Run this analysis pass over ``lines`` and return a result."""
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} name={self.name!r}>"
