"""Tests for verseflow.phonetics.

Assertions here are grounded in real CMU Pronouncing Dictionary data
(reasoned about, and independently confirmed by running the code in a
sandbox against the ``pronouncing`` package) -- not guesses.
"""

from __future__ import annotations

from verseflow import phonetics


def test_tokenize_words_strips_punctuation_keeps_apostrophes() -> None:
    line = "Flowin', can't stop -- won't stop!"
    assert phonetics.tokenize_words(line) == ["Flowin'", "can't", "stop", "won't", "stop"]


def test_iter_word_spans_offsets_are_correct() -> None:
    line = "cat hat"
    spans = phonetics.iter_word_spans(line)
    assert [s.word for s in spans] == ["cat", "hat"]
    assert (spans[0].start, spans[0].end) == (0, 3)
    assert (spans[1].start, spans[1].end) == (4, 7)
    assert line[spans[1].start : spans[1].end] == "hat"


def test_is_known_for_dictionary_and_oov_words() -> None:
    assert phonetics.is_known("rhythm") is True
    assert phonetics.is_known("love") is True
    # "flurbwomp" is not an English word and has no CMUdict entry.
    assert phonetics.is_known("flurbwomp") is False


def test_syllable_count_known_words() -> None:
    # "rhythm" -> R IH1 DH AH0 M -> 2 vowel phones (IH, AH) -> 2 syllables.
    assert phonetics.syllable_count("rhythm") == 2
    # "banana" -> 3 syllables, a standard textbook example.
    assert phonetics.syllable_count("banana") == 3
    # "cat" is a single, one-syllable word.
    assert phonetics.syllable_count("cat") == 1
    # "hustle" -> HH AH1 S AH0 L -> 2 syllables.
    assert phonetics.syllable_count("hustle") == 2


def test_syllable_count_falls_back_for_oov_words() -> None:
    # Not in CMUdict; falls back to vowel-cluster counting.
    # "flurbwomp" has two vowel clusters: "u" and "o".
    assert phonetics.syllable_count("flurbwomp") == phonetics.fallback_syllable_count(
        "flurbwomp"
    )
    assert phonetics.fallback_syllable_count("flurbwomp") == 2


def test_fallback_syllable_count_never_returns_zero() -> None:
    assert phonetics.fallback_syllable_count("xyz") == 1
    assert phonetics.fallback_syllable_count("") == 1


def test_stress_digits_known_word() -> None:
    # "rhythm" carries primary stress on its first (only stressed) syllable.
    assert phonetics.stress_digits("rhythm") == "10"
    # "banana" is stressed on the middle syllable: buh-NAN-uh.
    assert phonetics.stress_digits("banana") == "010"


def test_flow_symbols_maps_stress_to_ascii() -> None:
    assert phonetics.flow_symbols("rhythm") == "x-"
    assert phonetics.flow_symbols("banana") == "-x-"


def test_word_phonetics_bundle_for_known_word() -> None:
    info = phonetics.WordPhonetics.analyze("light")
    assert info.known is True
    assert info.syllables == 1
    assert info.flow == "x"
    assert info.phones is not None and "AY1" in info.phones


def test_word_phonetics_bundle_for_oov_word() -> None:
    info = phonetics.WordPhonetics.analyze("flurbwomp")
    assert info.known is False
    assert info.phones is None
    assert info.syllables >= 1
