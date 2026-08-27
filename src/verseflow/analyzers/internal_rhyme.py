"""Built-in analyzer: internal / multisyllabic rhyme chain detection.

Unlike :mod:`verseflow.analyzers.end_rhyme`, which only looks at the last
word of each line, this analyzer scans *every* word in the verse and
groups words that rhyme with each other regardless of where they sit in
a line -- this is what surfaces the internal and multisyllabic rhyme
chains that are characteristic of rap flow (e.g. a word in the middle of
line 2 rhyming with a word at the end of line 5).
"""

from __future__ import annotations

from typing import Any

from verseflow import phonetics, rhyme
from verseflow.analyzers import AnalysisResult, Analyzer

# Skip very short / structural words: they produce huge, meaningless
# "rhyme chains" (nearly every line has an "a" or "the" in it) that would
# drown out real content rhymes.
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "to", "of", "in", "on", "is", "it", "at",
        "and", "but", "or", "i", "my", "me", "so", "no", "up",
    }
)


class InternalRhymeAnalyzer(Analyzer):
    """Finds chains of 2+ words anywhere in the verse that share a rhyme.

    Words are grouped by exact rhyme-key match (see
    :func:`verseflow.rhyme.group_by_rhyme`); groups with only one member
    are dropped since a "chain" of one word isn't a rhyme relationship.
    Each retained word records the line and character span it was found
    at, so a renderer can highlight it in place.
    """

    name = "internal_rhyme"

    def analyze(self, lines: list[str]) -> AnalysisResult:
        occurrences: list[dict[str, Any]] = []
        for line_no, line in enumerate(lines, start=1):
            for span in phonetics.iter_word_spans(line):
                word_lower = span.word.lower()
                if word_lower in _STOPWORDS:
                    continue
                occurrences.append(
                    {
                        "word": span.word,
                        "line_no": line_no,
                        "start": span.start,
                        "end": span.end,
                    }
                )

        words = [o["word"] for o in occurrences]
        groups = rhyme.group_by_rhyme(words)

        chains: list[dict[str, Any]] = []
        chain_id = 0
        used_indices: set[int] = set()
        for group in groups:
            if len(group.words) < 2:
                continue
            # A group made up of repeated occurrences of the exact same
            # word (case-insensitive) is repetition, not a rhyme -- skip
            # it so real content rhymes aren't drowned out by e.g. "the"
            # ... "the" or "every" ... "every" showing up as a "chain".
            if len({w.lower() for w in group.words}) < 2:
                continue
            members: list[dict[str, Any]] = []
            for word in group.words:
                # Find the next not-yet-used occurrence of this exact word
                # so repeated words map to distinct positions.
                for idx, occ in enumerate(occurrences):
                    if idx in used_indices:
                        continue
                    if occ["word"] == word:
                        used_indices.add(idx)
                        members.append(occ)
                        break
            chains.append(
                {
                    "id": chain_id,
                    "rhyme_key": group.label_key,
                    "words": members,
                }
            )
            chain_id += 1

        summary_lines = []
        if not chains:
            summary_lines.append("No internal rhyme chains found (2+ shared-rhyme words).")
        for chain in chains:
            word_list = ", ".join(f"{m['word']} (line {m['line_no']})" for m in chain["words"])
            summary_lines.append(f"Chain {chain['id']} [{chain['rhyme_key']}]: {word_list}")

        return AnalysisResult(
            analyzer=self.name,
            summary="\n".join(summary_lines),
            data={"chains": chains},
        )


def get_analyzer() -> Analyzer:
    """Entry-point factory used by verseflow's plugin registry."""
    return InternalRhymeAnalyzer()
