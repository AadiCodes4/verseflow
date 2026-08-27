"""Built-in analyzer: stressed/unstressed rhythm ("flow") pattern per line."""

from __future__ import annotations

from verseflow import phonetics
from verseflow.analyzers import AnalysisResult, Analyzer


class FlowPatternAnalyzer(Analyzer):
    """Renders each line's stress pattern as ASCII flow notation.

    Each word contributes one ``x`` (stressed syllable) or ``-``
    (unstressed syllable) per syllable, e.g. "Grinding through the
    midnight" -> "x- x x- x-" (word-separated) and "x-xx-x-" (concatenated).
    Both forms are provided in the structured data; the summary uses the
    word-separated form for readability.
    """

    name = "flow_pattern"

    def analyze(self, lines: list[str]) -> AnalysisResult:
        line_data = []
        for line_no, line in enumerate(lines, start=1):
            words = phonetics.tokenize_words(line)
            per_word = [phonetics.flow_symbols(w) for w in words]
            pattern_spaced = " ".join(per_word)
            pattern_compact = "".join(per_word)
            line_data.append(
                {
                    "line_no": line_no,
                    "text": line,
                    "words": words,
                    "pattern_spaced": pattern_spaced,
                    "pattern_compact": pattern_compact,
                    "syllables": len(pattern_compact),
                }
            )

        summary_lines = []
        for entry in line_data:
            summary_lines.append(f"{entry['line_no']:>2}: {entry['text']}")
            summary_lines.append(f"    {entry['pattern_spaced']}")

        return AnalysisResult(
            analyzer=self.name,
            summary="\n".join(summary_lines),
            data={"lines": line_data},
        )


def get_analyzer() -> Analyzer:
    """Entry-point factory used by verseflow's plugin registry."""
    return FlowPatternAnalyzer()
