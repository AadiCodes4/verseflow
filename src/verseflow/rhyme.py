"""Core rhyme-matching logic.

The central idea (standard in computational rhyme detection) is the
**rhyming part** of a word: the phoneme sequence starting at its last
*stressed* vowel and running to the end of the word. Two words rhyme if
their rhyming parts match. "night" (N AY1 T) and "light" (L AY1 T) both
have the rhyming part "AY1 T" -- they rhyme. "fire" (F AY1 ER0) and
"desire" (D IH0 Z AY1 ER0) both end in "AY1 ER0" -- they rhyme too, even
though "desire" has an extra unstressed syllable in front, which is
exactly how multisyllabic rap rhymes work.

``pronouncing.rhyming_part`` implements this extraction for us using real
CMUdict phoneme data. For words that are not in the dictionary we fall
back to a much cruder, clearly-approximate heuristic based on spelling.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Literal

import pronouncing

from verseflow import phonetics

RhymeType = Literal["exact", "near"]

# Below this phoneme-similarity ratio, two words are considered unrelated.
# Between this value and an exact match, they're a "near" / slant rhyme.
NEAR_RHYME_THRESHOLD = 0.6

_TRAILING_CONSONANT_RE = re.compile(r"[^aeiouy]*$", re.IGNORECASE)
_FALLBACK_VOWEL_TAIL_RE = re.compile(r"[aeiouy]+[^aeiouy]*$", re.IGNORECASE)


def rhyming_part(word: str) -> tuple[str, ...] | None:
    """Return the rhyming part of ``word`` as a tuple of ARPAbet phones.

    Returns ``None`` if the word cannot be analyzed at all (empty string).
    For dictionary words this is real phoneme data taken from the last
    stressed vowel onward. For out-of-dictionary words we fall back to
    :func:`_fallback_rhyme_key`, a spelling-based approximation -- this is
    clearly weaker than real phonetics and is documented as such.
    """
    if not word:
        return None

    pron = phonetics.best_pronunciation(word)
    if pron is not None:
        part = pronouncing.rhyming_part(pron)
        if part:
            return tuple(part.split())
        # `pronouncing.rhyming_part` can return an empty string for words
        # with no stressed vowel in some CMUdict entries (rare, mostly
        # function words); fall through to the spelling heuristic.

    return _fallback_rhyme_key(word)


def _fallback_rhyme_key(word: str) -> tuple[str, ...]:
    """Approximate a rhyme key from spelling alone, for out-of-dictionary words.

    This is a heuristic, NOT phonetics: it takes the trailing
    "vowel-cluster + following consonants" chunk of the written word
    (e.g. "womp" -> "omp", "flurb" -> "u" + "rb" -> "urb") and treats each
    letter as its own pseudo-phone so it can still be compared with
    :func:`rhyme_similarity`. It exists only so slang / made-up words that
    aren't in the CMU dictionary can still participate in rhyme grouping
    instead of being silently dropped.
    """
    w = word.lower()
    match = _FALLBACK_VOWEL_TAIL_RE.search(w)
    tail = match.group(0) if match else w
    # Represent each letter as a one-character "pseudo-phone" so the
    # sequence-similarity comparison in rhyme_similarity() still works.
    return tuple(tail)


def normalized_rhyme_key(word: str) -> tuple[str, ...] | None:
    """Return ``word``'s rhyming part with stress digits removed.

    Two words with the same normalized key are judged to rhyme *exactly*
    (stress placement can differ slightly, e.g. compound words, without
    breaking a rhyme -- what matters for grouping is the vowel/consonant
    sequence).
    """
    part = rhyming_part(word)
    if part is None:
        return None
    return tuple(phonetics.strip_stress(p) for p in part)


def rhyme_similarity(word_a: str, word_b: str) -> float:
    """Return a 0.0-1.0 phoneme-similarity score between two words' rhyme parts.

    Computed with :class:`difflib.SequenceMatcher` over the stress-stripped
    rhyming-part phoneme sequences. 1.0 means the rhyme parts are
    identical (a perfect/exact rhyme candidate); lower scores indicate
    partial ("near"/slant) similarity.
    """
    key_a = normalized_rhyme_key(word_a)
    key_b = normalized_rhyme_key(word_b)
    if not key_a or not key_b:
        return 0.0
    return difflib.SequenceMatcher(None, key_a, key_b).ratio()


def classify_rhyme(word_a: str, word_b: str) -> RhymeType | None:
    """Classify the rhyme relationship between two words.

    Returns:
        ``"exact"``  -- the words' normalized rhyming parts are identical.
        ``"near"``   -- the words share their stressed vowel and enough of
                         the trailing phonemes to sound like a slant rhyme
                         (similarity >= :data:`NEAR_RHYME_THRESHOLD`).
        ``None``     -- the words don't rhyme.

    Two single-letter or otherwise degenerate rhyme keys never classify
    as rhyming (avoids spurious matches on very short fallback words).
    """
    if word_a.lower() == word_b.lower():
        return None  # identical words are not considered a "rhyme" of themselves

    key_a = normalized_rhyme_key(word_a)
    key_b = normalized_rhyme_key(word_b)
    if not key_a or not key_b:
        return None

    if key_a == key_b:
        return "exact"

    # A near rhyme should still share its stressed vowel sound -- otherwise
    # two words with merely one trailing consonant in common (e.g. "cat"
    # and "sit") would false-positive on sequence similarity alone.
    if key_a[0] != key_b[0]:
        return None

    similarity = rhyme_similarity(word_a, word_b)
    if similarity >= NEAR_RHYME_THRESHOLD:
        return "near"
    return None


def rhymes(word_a: str, word_b: str) -> bool:
    """Convenience predicate: True if ``word_a`` and ``word_b`` rhyme at all (exact or near)."""
    return classify_rhyme(word_a, word_b) is not None


@dataclass(frozen=True)
class RhymeGroup:
    """A set of words that all rhyme with each other, in first-seen order."""

    key: tuple[str, ...]
    words: tuple[str, ...]

    @property
    def label_key(self) -> str:
        """A short human-readable string for this group's shared sound, e.g. 'AY-T'."""
        return "-".join(self.key) if self.key else "?"


def group_by_rhyme(words: list[str]) -> list[RhymeGroup]:
    """Group a list of words into rhyme chains using exact rhyme-key matching.

    Words are assigned to the first existing group whose key matches
    exactly; unmatched words start a new group. Groups of size 1 (a word
    that doesn't rhyme with anything else in the input) are still
    returned, since callers may want to distinguish "rhymes with nothing"
    from "wasn't analyzed".

    Order of groups reflects first appearance, and words within a group
    keep first-appearance order too, which keeps output deterministic.
    """
    groups: list[list[str]] = []
    keys: list[tuple[str, ...] | None] = []

    for word in words:
        key = normalized_rhyme_key(word)
        placed = False
        for i, existing_key in enumerate(keys):
            if key is not None and key == existing_key:
                groups[i].append(word)
                placed = True
                break
        if not placed:
            groups.append([word])
            keys.append(key)

    return [
        RhymeGroup(key=key or (), words=tuple(group))
        for key, group in zip(keys, groups, strict=True)
    ]
