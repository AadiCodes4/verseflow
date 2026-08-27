"""Phoneme, syllable, and stress lookups.

This module is the single place where verseflow talks to the CMU
Pronouncing Dictionary (via the ``pronouncing`` package). Everything else
in the project -- rhyme detection, flow-pattern rendering, the syllable
analyzer -- goes through the small set of functions defined here so that
the "what do we do when a word isn't in the dictionary" decision is made
in exactly one place.

CMU dictionary phones are ARPAbet symbols such as ``"AH1"`` (a vowel with
primary stress) or ``"V"`` (a consonant, which never carries a stress
digit). Vowel phones are followed by a stress marker:

* ``0`` -- unstressed
* ``1`` -- primary stress
* ``2`` -- secondary stress
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import pronouncing

# The 15 ARPAbet vowel symbols (CMUdict), without stress digits.
ARPABET_VOWELS = frozenset(
    {
        "AA", "AE", "AH", "AO", "AW", "AY",
        "EH", "ER", "EY", "IH", "IY",
        "OW", "OY", "UH", "UW",
    }
)

_STRESS_DIGIT_RE = re.compile(r"[0-9]$")
_WORD_RE = re.compile(r"[A-Za-z']+")
_VOWEL_CLUSTER_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)


def tokenize_words(line: str) -> list[str]:
    """Split a line of lyrics into word tokens.

    Punctuation is dropped, but internal apostrophes (``"can't"``,
    ``"flowin'"``) are preserved because they matter for dictionary
    lookups and for fallback syllable counting.
    """
    return _WORD_RE.findall(line)


@dataclass(frozen=True)
class WordSpan:
    """A word token together with its character offsets within its source line."""

    word: str
    start: int
    end: int


def iter_word_spans(line: str) -> list[WordSpan]:
    """Like :func:`tokenize_words`, but also returns each word's ``[start, end)``
    character offsets within ``line``. Used by analyzers/renderers that need
    to highlight specific words in their original text position (e.g. the
    HTML report).
    """
    return [WordSpan(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(line)]


def is_vowel_phone(phone: str) -> bool:
    """Return True if an ARPAbet phone (with or without stress digit) is a vowel."""
    return strip_stress(phone) in ARPABET_VOWELS


def strip_stress(phone: str) -> str:
    """Remove the trailing stress digit from a single ARPAbet phone, if present."""
    return _STRESS_DIGIT_RE.sub("", phone)


@lru_cache(maxsize=4096)
def pronunciations(word: str) -> tuple[str, ...]:
    """Return every known CMUdict pronunciation of ``word``, each as a phone string.

    Results are cached because the same word (e.g. "the", "like") tends to
    recur across many lines of a verse and dictionary lookups are the hot
    path of the whole pipeline.
    """
    return tuple(pronouncing.phones_for_word(word.lower()))


def is_known(word: str) -> bool:
    """Return True if ``word`` has at least one CMUdict entry."""
    return len(pronunciations(word)) > 0


def best_pronunciation(word: str) -> str | None:
    """Return CMUdict's first (most common) pronunciation of ``word``, or None."""
    prons = pronunciations(word)
    return prons[0] if prons else None


def phones_list(word: str) -> list[str] | None:
    """Return the phone list for ``word``'s primary pronunciation, or None if unknown."""
    pron = best_pronunciation(word)
    return pron.split() if pron is not None else None


# --------------------------------------------------------------------------
# Fallback heuristics for words that are not in the CMU Pronouncing
# Dictionary (slang, ad-libs, names, typos, made-up words -- all common in
# rap/R&B lyrics). These are deliberately simple approximations: they are
# never as accurate as real phoneme data, and every function below says so.
# --------------------------------------------------------------------------


def fallback_syllable_count(word: str) -> int:
    """Approximate a word's syllable count by counting vowel clusters.

    This is a heuristic, NOT a phonetic analysis -- it is only used when a
    word has no CMUdict entry. The algorithm:

    1. Count contiguous runs of ``a e i o u y`` as one syllable each.
    2. Drop a trailing silent "e" (e.g. "flowerin'" -> "flowerin", but
       "the" -> "th" would be wrong, so this rule is skipped for words
       that would be reduced to zero vowel clusters).
    3. Never return less than 1 for a non-empty word, since every English
       word has at least one syllable.
    """
    w = word.lower()
    clusters = _VOWEL_CLUSTER_RE.findall(w)
    count = len(clusters)

    # Drop a silent trailing "e" (e.g. "game", "vibe") -- but only if doing
    # so doesn't erase the word's only vowel cluster.
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and count > 1:
        count -= 1

    return max(count, 1)


def fallback_stress_pattern(syllable_count: int) -> str:
    """Guess a stress pattern of '1'/'0' digits for a word with no dictionary entry.

    We have no real prosodic information for out-of-vocabulary words, so
    this assumes the common English tendency to stress the first syllable
    of a word and alternate from there (trochaic fallback). It is a rough
    placeholder, clearly inferior to a real dictionary lookup, and exists
    only so the flow-pattern analyzer can still emit *something* for every
    word in a verse.
    """
    if syllable_count <= 0:
        return ""
    return "".join("1" if i % 2 == 0 else "0" for i in range(syllable_count))


def syllable_count(word: str) -> int:
    """Return the syllable count for ``word``.

    Uses ``pronouncing.syllable_count`` (derived from real CMUdict phoneme
    data) whenever the word is known, and falls back to
    :func:`fallback_syllable_count` (a vowel-cluster approximation)
    otherwise.
    """
    pron = best_pronunciation(word)
    if pron is not None:
        return pronouncing.syllable_count(pron)
    return fallback_syllable_count(word)


def stress_digits(word: str) -> str:
    """Return the per-syllable stress digits for ``word`` as a string like ``"010"``.

    Uses ``pronouncing.stresses`` for known words. For unknown words, falls
    back to :func:`fallback_stress_pattern`, which is an approximation.
    """
    pron = best_pronunciation(word)
    if pron is not None:
        return pronouncing.stresses(pron)
    return fallback_stress_pattern(fallback_syllable_count(word))


def flow_symbols(word: str) -> str:
    """Render a word's stress pattern as ASCII flow notation.

    Primary/secondary stress ('1' / '2') becomes ``x`` (a hit / downbeat);
    unstressed ('0') becomes ``-``. E.g. "rhythm" (stresses "10") -> "x-".
    """
    digits = stress_digits(word)
    return "".join("x" if d in ("1", "2") else "-" for d in digits)


@dataclass(frozen=True)
class WordPhonetics:
    """A bundle of everything verseflow knows about one word's pronunciation."""

    word: str
    known: bool
    phones: tuple[str, ...] | None
    syllables: int
    stress: str
    flow: str

    @classmethod
    def analyze(cls, word: str) -> WordPhonetics:
        pron = best_pronunciation(word)
        known = pron is not None
        return cls(
            word=word,
            known=known,
            phones=tuple(pron.split()) if pron else None,
            syllables=syllable_count(word),
            stress=stress_digits(word),
            flow=flow_symbols(word),
        )
