# verseflow

[![CI](https://github.com/AadiCodes4/verseflow/actions/workflows/ci.yml/badge.svg)](https://github.com/AadiCodes4/verseflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)

Analyzes rhyme scheme, internal/multisyllabic rhyme chains, syllable counts, and stress pattern ("flow") in verse — rap, R&B, poetry, whatever text you point it at.

Give it lines of text and it'll tell you:

- **syllables** per word and per line, from real CMU Pronouncing Dictionary phoneme data, with a spelling-based fallback for words that aren't in the dictionary
- **end rhyme scheme** — groups lines by their last word's rhyme, reported as `AABB`, `ABAB`, etc.
- **internal / multisyllabic rhyme chains** — words *anywhere* in the verse that rhyme with each other, not just at line endings, which is where a lot of rap's more interesting rhyme patterns actually live
- **flow pattern** — each line's stress pattern as ascii (`x` = stressed, `-` = unstressed)

## Install

```bash
pip install -e ".[dev]"
```

Depends on [`pronouncing`](https://pypi.org/project/pronouncing/), a thin pure-Python wrapper around the public-domain CMU Pronouncing Dictionary. Requires Python 3.10+.

## CLI

```
verseflow analyze poem.txt --format ascii|json|html [--analyzers name,name] [-o out]
verseflow demo --format ascii|json|html
verseflow list-analyzers
```

`analyze` runs the pipeline over a UTF-8 text file (one lyric line per line). `demo` runs it over a short original verse shipped with the package, for trying it out with zero setup. `--analyzers` restricts the run to specific analyzers by name; leave it off to run everything installed.

## How the rhyme check works

Two words rhyme if the phoneme sequence from the last *stressed* vowel to the end of the word matches. "night" (`N AY1 T`) and "light" (`L AY1 T`) share `AY1 T`. "fire" (`F AY1 ER0`) and "desire" (`D IH0 Z AY1 ER0`) both end in `AY1 ER0` even with different syllable counts — that's how multisyllabic rhymes work. Words outside the dictionary fall back to a spelling-based approximation.

Near/slant rhymes ("rhythm" / "system") are caught separately, by comparing stress-stripped rhyme parts with `difflib.SequenceMatcher` once the stressed vowels match.

```pycon
>>> from verseflow import rhyme
>>> rhyme.classify_rhyme("night", "light")
'exact'
>>> rhyme.classify_rhyme("fire", "desire")
'exact'
>>> rhyme.classify_rhyme("rhythm", "system")
'near'
>>> rhyme.classify_rhyme("cat", "bag")
# None
```

## Plugin architecture

The four built-in analyzers (`syllables`, `end_rhyme`, `internal_rhyme`, `flow_pattern`) aren't special-cased — they're registered through the `verseflow.analyzers` entry-point group in `pyproject.toml`, the same way a third-party analyzer would be:

```toml
[project.entry-points."verseflow.analyzers"]
syllables = "verseflow.analyzers.syllables:get_analyzer"
end_rhyme = "verseflow.analyzers.end_rhyme:get_analyzer"
internal_rhyme = "verseflow.analyzers.internal_rhyme:get_analyzer"
flow_pattern = "verseflow.analyzers.flow_pattern:get_analyzer"
```

`verseflow.plugins.AnalyzerRegistry` discovers entries under that group via `importlib.metadata` at runtime, so a package installed alongside verseflow that declares the same group shows up in `list-analyzers` and the pipeline automatically. One broken analyzer's error is captured per-analyzer rather than taking the whole run down.

Writing one is small:

```python
from verseflow.analyzers import AnalysisResult, Analyzer
from verseflow import phonetics

class AlliterationAnalyzer(Analyzer):
    """Longest run of consecutive same-initial-sound words per line."""
    name = "alliteration"

    def analyze(self, lines: list[str]) -> AnalysisResult:
        line_data = []
        for line_no, line in enumerate(lines, start=1):
            words = phonetics.tokenize_words(line)
            streak = best = 1
            for prev, word in zip(words, words[1:]):
                streak = streak + 1 if prev[0].lower() == word[0].lower() else 1
                best = max(best, streak)
            line_data.append({"line_no": line_no, "text": line, "longest_streak": best})
        summary = "\n".join(f"{e['line_no']}: streak {e['longest_streak']}" for e in line_data)
        return AnalysisResult(analyzer=self.name, summary=summary, data={"lines": line_data})

def get_analyzer() -> Analyzer:
    return AlliterationAnalyzer()
```

```toml
# your own pyproject.toml
[project.entry-points."verseflow.analyzers"]
alliteration = "my_verseflow_plugin.wordplay:get_analyzer"
```

`pip install` it next to verseflow and it shows up in `verseflow list-analyzers` automatically. See `CONTRIBUTING.md` for the full guide, including programmatic registration for quick local testing.

## Example

The demo verse below was written specifically for this project — no real song lyrics appear anywhere in verseflow.

```
Grinding through the midnight while the city lights stay low
Chasing bigger visions than the shadows used to throw
Every ounce of hustle turns my worries into gold
Still the fire in my spirit burning steady, burning bold
Steady on the pavement with my vision set on prize
Building up a future that no distance can disguise
Every word I'm speaking turns the struggle to design
Nothing but the grind and a clear mind until they align
```

`verseflow demo --format ascii` (colors are stripped here for markdown, but a real terminal shows one color per rhyme group/chain):

```
== end_rhyme ==
[A] low / throw     [B] gold / bold     [C] prize / disguise     [D] design / align
Scheme: AABBCCDD

== internal_rhyme ==
Chain 5 [AY-Z]: prize (line 5), disguise (line 6)
Chain 6 [AY-N]: design (line 7), align (line 8)
Chain 7 [AY-N-D]: grind (line 8), mind (line 8)
... (8 chains total)

== flow_pattern ==
 1: Grinding through the midnight while the city lights stay low
    x- x - xx x - x- x x x

== syllables ==
Total syllables: 109
```

Note that `internal_rhyme` catches things `end_rhyme` alone would miss entirely — `grind` and `mind` both mid-line-8, `Still` (start of line 4) rhyming with `until` (mid-line 8). `--format html` writes a single self-contained file (inline CSS/JS, no CDN) that highlights every rhyme group/chain over the lyrics in its own color, with toggles per layer.

## Tests

```
$ pytest -q
46 passed in 0.32s
```

Includes a test that entry-point discovery genuinely finds all four built-in analyzers (not mocked), plus assertions against specific phonetic facts — "rhythm" has 2 syllables, "night"/"light" rhyme exactly, "cat"/"bag" don't rhyme, and so on.

## Layout

```
src/verseflow/
  phonetics.py        # CMUdict lookups + fallback heuristics
  rhyme.py             # rhyme-part extraction + exact/near classification
  plugins.py           # analyzer registry + run_pipeline()
  render.py            # ANSI terminal output + standalone HTML report
  cli.py               # entry point
  analyzers/
    syllables.py, end_rhyme.py, internal_rhyme.py, flow_pattern.py
tests/
.github/               # CI, issue/PR templates
```

## Contributing

See `CONTRIBUTING.md` for dev setup and the analyzer-plugin guide, and `CODE_OF_CONDUCT.md` for community norms.

## A note on lyrics

Every example verse in this repo — CLI demo, tests, this README — is original text written for verseflow. No real song lyrics, artists, or titles appear anywhere in the project.

## License

[MIT](LICENSE) © 2026 Aadi Arya
