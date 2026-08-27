"""Built-in analyzer: per-line and per-word syllable counts."""

from __future__ import annotations

from typing import Any

from verseflow import phonetics
from verseflow.analyzers import AnalysisResult, Analyzer


class SyllablesAnalyzer(Analyzer):
    """Counts syllables per word and per line using CMUdict phoneme data.

    Falls back to a vowel-cluster heuristic (see
    :func:`verseflow.phonetics.fallback_syllable_count`) for any word
    that isn't in the CMU Pronouncing Dictionary.
    """

    name = "syllables"

    def analyze(self, lines: list[str]) -> AnalysisResult:
        line_data: list[dict[str, Any]] = []
        total = 0

        for line_no, line in enumerate(lines, start=1):
            words = phonetics.tokenize_words(line)
            word_data: list[dict[str, Any]] = []
            line_total = 0
            for word in words:
                count = phonetics.syllable_count(word)
                known = phonetics.is_known(word)
                word_data.append({"word": word, "syllables": count, "known": known})
                line_total += count
            line_data.append(
                {
                    "line_no": line_no,
                    "text": line,
                    "words": word_data,
                    "syllables": line_total,
                }
            )
            total += line_total

        summary_lines = [
            f"{entry['line_no']:>2} ({entry['syllables']:>2} syl)  "
            + " ".join(f"{w['word']}({w['syllables']})" for w in entry["words"])
            for entry in line_data
        ]
        summary_lines.append(f"\nTotal syllables: {total}")

        return AnalysisResult(
            analyzer=self.name,
            summary="\n".join(summary_lines),
            data={"lines": line_data, "total_syllables": total},
        )


def get_analyzer() -> Analyzer:
    """Entry-point factory used by verseflow's plugin registry."""
    return SyllablesAnalyzer()
