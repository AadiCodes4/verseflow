"""Built-in analyzer: end-rhyme scheme detection (AABB / ABAB / etc.)."""

from __future__ import annotations

from string import ascii_uppercase
from typing import Any

from verseflow import phonetics, rhyme
from verseflow.analyzers import AnalysisResult, Analyzer


def _scheme_label(index: int) -> str:
    """Turn a 0-based group index into a scheme letter: 0->A, 1->B, ..., 25->Z, 26->AA, ..."""
    letters = []
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters.append(ascii_uppercase[remainder])
    return "".join(reversed(letters))


def _last_word(line: str) -> str | None:
    words = phonetics.tokenize_words(line)
    return words[-1] if words else None


class EndRhymeAnalyzer(Analyzer):
    """Groups lines by their end-word rhyme and reports the resulting scheme.

    Each line's last word is compared against the *representative* word of
    every rhyme group seen so far (the first end word placed in that
    group). An exact rhyme match reuses that group's letter; a near/slant
    rhyme also joins the group but is flagged as such; otherwise the line
    starts a new group. The result is a scheme string like ``"AABB"``,
    the same notation used in poetry analysis.
    """

    name = "end_rhyme"

    def analyze(self, lines: list[str]) -> AnalysisResult:
        group_representatives: list[str] = []
        line_entries: list[dict[str, Any]] = []

        for line_no, line in enumerate(lines, start=1):
            end_word = _last_word(line)
            label = None
            rhyme_type = None

            if end_word is not None:
                for i, rep in enumerate(group_representatives):
                    rtype = rhyme.classify_rhyme(end_word, rep)
                    if rtype is not None:
                        label = _scheme_label(i)
                        rhyme_type = rtype
                        break
                if label is None:
                    group_representatives.append(end_word)
                    label = _scheme_label(len(group_representatives) - 1)
                    rhyme_type = "exact"  # a group's founding member trivially matches itself

            line_entries.append(
                {
                    "line_no": line_no,
                    "text": line,
                    "end_word": end_word,
                    "label": label,
                    "rhyme_type": rhyme_type,
                }
            )

        scheme = "".join(entry["label"] or "?" for entry in line_entries)

        summary_lines = [
            f"{entry['label'] or '?'}  ({entry['rhyme_type'] or 'n/a':>5})  "
            f"line {entry['line_no']}: ...{entry['end_word'] or ''}"
            for entry in line_entries
        ]
        summary_lines.append(f"\nScheme: {scheme}")

        return AnalysisResult(
            analyzer=self.name,
            summary="\n".join(summary_lines),
            data={"scheme": scheme, "lines": line_entries},
        )


def get_analyzer() -> Analyzer:
    """Entry-point factory used by verseflow's plugin registry."""
    return EndRhymeAnalyzer()
