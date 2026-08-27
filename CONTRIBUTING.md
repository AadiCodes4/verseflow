# Contributing to verseflow

Thanks for considering a contribution! verseflow is a small, focused
toolkit, and its plugin architecture means most new *analysis features*
don't need to touch verseflow's own source at all -- see
[Adding a new analyzer](#adding-a-new-analyzer-third-party-plugin) below.

## Development setup

```bash
git clone https://github.com/AadiCodes4/verseflow.git
cd verseflow
python3 -m venv .venv
source .venv/bin/activate          # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

This installs verseflow in editable mode along with its dev dependencies
(`pytest`, `mypy`, `ruff`) and registers the built-in analyzers'
entry points, so `verseflow list-analyzers` should immediately show all
four:

```bash
$ verseflow list-analyzers
Registered analyzers:
  - end_rhyme
  - flow_pattern
  - internal_rhyme
  - syllables
```

### Running the checks CI runs

```bash
ruff check .        # lint
mypy src             # type-check the package
pytest -q            # run the test suite
```

All three must pass before a PR can be merged; CI runs them on
Python 3.10, 3.11, and 3.12 (see `.github/workflows/ci.yml`).

### Project layout

```
src/verseflow/
  phonetics.py      # CMUdict lookups + syllable/stress fallback heuristics
  rhyme.py           # rhyme-part extraction, exact/near rhyme classification
  plugins.py         # the analyzer registry + run_pipeline()
  render.py          # ANSI terminal output + standalone HTML report
  cli.py             # `verseflow` command-line entry point
  analyzers/
    __init__.py       # the Analyzer ABC and AnalysisResult dataclass
    syllables.py
    end_rhyme.py
    internal_rhyme.py
    flow_pattern.py
tests/               # pytest suite, one file per module above
```

## Adding a new analyzer (third-party plugin)

This is the main extensibility point in verseflow, and you do **not**
need to fork or vendor verseflow to do it. An analyzer is any class that
implements the two-member `Analyzer` contract from
`verseflow.analyzers`:

```python
# my_verseflow_plugin/wordplay.py
from verseflow.analyzers import AnalysisResult, Analyzer
from verseflow import phonetics


class AlliterationAnalyzer(Analyzer):
    """Counts consecutive words in each line that start with the same sound."""

    name = "alliteration"

    def analyze(self, lines: list[str]) -> AnalysisResult:
        line_data = []
        for line_no, line in enumerate(lines, start=1):
            words = phonetics.tokenize_words(line)
            streak = 1
            best = 1
            for prev, word in zip(words, words[1:]):
                if prev[0].lower() == word[0].lower():
                    streak += 1
                    best = max(best, streak)
                else:
                    streak = 1
            line_data.append({"line_no": line_no, "text": line, "longest_streak": best})

        summary = "\n".join(f"{e['line_no']}: longest streak {e['longest_streak']}" for e in line_data)
        return AnalysisResult(analyzer=self.name, summary=summary, data={"lines": line_data})


def get_analyzer() -> Analyzer:
    return AlliterationAnalyzer()
```

Then, in **your own package's** `pyproject.toml`, register it under the
`verseflow.analyzers` entry-point group -- the same group verseflow uses
for its own built-in analyzers:

```toml
[project]
name = "my-verseflow-plugin"
dependencies = ["verseflow"]

[project.entry-points."verseflow.analyzers"]
alliteration = "my_verseflow_plugin.wordplay:get_analyzer"
```

Once your package is installed alongside verseflow (`pip install -e .` in
your plugin's directory is enough for local development), it shows up
automatically -- no changes to verseflow's source, no registry file to
edit by hand:

```bash
$ verseflow list-analyzers
Registered analyzers:
  - alliteration
  - end_rhyme
  - flow_pattern
  - internal_rhyme
  - syllables

$ verseflow demo --format json --analyzers alliteration
```

A few notes on writing a well-behaved analyzer:

- `name` must be unique and non-empty; `AnalyzerRegistry.register` raises
  `ValueError` on a collision unless called with `override=True`.
- `analyze()` receives the lyric text as a `list[str]` with blank lines
  already stripped out, and must return one `AnalysisResult`
  (`summary: str` for human-readable/CLI output, `data: dict` for
  JSON/HTML consumers). Keep `data` JSON-serializable.
- An analyzer that raises is not fatal to the rest of the pipeline:
  `run_pipeline()` catches the exception and records it as an
  `{"error": ...}` result for that analyzer only, so one broken plugin
  never breaks the others. Still, try not to raise -- write real tests.
- The registry supports entry points pointing at a class, a zero-argument
  factory function (as in the example above), or a ready-made instance --
  pick whichever is most convenient for your plugin.

If you'd rather not publish a separate package while developing, you can
also register an analyzer programmatically in-process:

```python
from verseflow.plugins import register_analyzer
from my_verseflow_plugin.wordplay import AlliterationAnalyzer

register_analyzer(AlliterationAnalyzer())
```

## A note on lyric content

verseflow ships with exactly one demo verse (`verseflow.cli.DEMO_VERSE`),
written from scratch for this project. Please do not add real song
lyrics, real artist names, or real song/album titles anywhere in the
repository (code, tests, fixtures, docs, issues, or PRs) -- verseflow
only ever ships original example text.

## Submitting changes

1. Fork the repo and create a branch off `main`.
2. Make your change, with tests (see `tests/` for the existing style --
   concrete assertions grounded in real, verifiable phonetics wherever
   possible, not vague "doesn't crash" checks).
3. Run `ruff check .`, `mypy src`, and `pytest -q` locally.
4. Open a pull request describing what changed and why; fill out the PR
   template.

Bug reports and feature requests are welcome via GitHub Issues -- please
use the provided templates.
