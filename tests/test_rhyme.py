"""Tests for verseflow.rhyme.

Word pairs are chosen because their pronunciations are well known /
independently verifiable via CMUdict, and were confirmed by running
``pronouncing`` directly against them in a sandbox before being encoded
here as assertions.
"""

from __future__ import annotations

from verseflow import rhyme


def test_exact_rhyme_single_syllable_pairs() -> None:
    # night: N AY1 T / light: L AY1 T -> identical rhyming part "AY1 T"
    assert rhyme.classify_rhyme("night", "light") == "exact"
    # cat: K AE1 T / hat: HH AE1 T -> identical rhyming part "AE1 T"
    assert rhyme.classify_rhyme("cat", "hat") == "exact"
    # flow: F L OW1 / glow: G L OW1
    assert rhyme.classify_rhyme("flow", "glow") == "exact"
    # grind: G R AY1 N D / mind: M AY1 N D
    assert rhyme.classify_rhyme("grind", "mind") == "exact"


def test_exact_rhyme_across_different_syllable_counts() -> None:
    # fire: F AY1 ER0 (2 syl) / desire: D IH0 Z AY1 ER0 (3 syl) -- both end
    # in the rhyming part "AY1 ER0". This is the multisyllabic-rhyme case:
    # an extra unstressed syllable up front does not break the rhyme.
    assert rhyme.classify_rhyme("fire", "desire") == "exact"


def test_non_rhyming_words_return_none() -> None:
    # cat: AE1 T / bag: AE1 G -- share a vowel but not the final consonant,
    # and score well below the near-rhyme threshold.
    assert rhyme.classify_rhyme("cat", "bag") is None
    # completely unrelated words.
    assert rhyme.classify_rhyme("hustle", "orange") is None


def test_identical_word_is_not_a_rhyme_of_itself() -> None:
    assert rhyme.classify_rhyme("flow", "flow") is None
    assert rhyme.classify_rhyme("Flow", "flow") is None  # case-insensitive


def test_near_rhyme_slant_pair() -> None:
    # rhythm: R IH1 DH AH0 M / system: S IH1 S T AH0 M -- share the
    # stressed vowel IH and the final "AH0 M", but differ in the middle
    # consonant cluster (DH vs S T). A classic slant/near rhyme.
    assert rhyme.classify_rhyme("rhythm", "system") == "near"


def test_rhymes_predicate() -> None:
    assert rhyme.rhymes("low", "throw") is True
    assert rhyme.rhymes("low", "hustle") is False


def test_rhyming_part_extraction() -> None:
    assert rhyme.rhyming_part("night") == ("AY1", "T")
    assert rhyme.rhyming_part("cat") == ("AE1", "T")


def test_normalized_rhyme_key_strips_stress_digits() -> None:
    key = rhyme.normalized_rhyme_key("night")
    assert key is not None
    assert all(not ch[-1].isdigit() for ch in key)
    assert key == ("AY", "T")


def test_group_by_rhyme_forms_expected_chains() -> None:
    words = ["night", "day", "light", "way", "bright"]
    groups = rhyme.group_by_rhyme(words)
    # night/light/bright share "AY T"; day/way share "EY".
    chain_sets = [set(g.words) for g in groups]
    assert {"night", "light", "bright"} in chain_sets
    assert {"day", "way"} in chain_sets


def test_fallback_rhyme_key_for_out_of_dictionary_words() -> None:
    # Neither word is in CMUdict, but they share a spelling-based trailing
    # vowel-consonant chunk, so the heuristic fallback should still let
    # them be classified as rhyming with each other.
    result = rhyme.classify_rhyme("zoomtastic", "boomtastic")
    assert result in ("exact", "near")
