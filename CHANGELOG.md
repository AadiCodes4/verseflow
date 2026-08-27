# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-27

### Added

- Initial public release of verseflow.
- Core phonetics module (`verseflow.phonetics`) built on the `pronouncing`
  package (CMU Pronouncing Dictionary), with a documented vowel-cluster
  fallback for out-of-dictionary words.
- Core rhyme-matching module (`verseflow.rhyme`): rhyming-part extraction,
  exact/near (slant) rhyme classification, and rhyme-group formation.
- Plugin architecture (`verseflow.plugins`): an `AnalyzerRegistry` that
  discovers analyzers via the `verseflow.analyzers` Python entry-point
  group, plus `register_analyzer`, `get_analyzer`, `list_analyzers`, and
  `run_pipeline`.
- Four built-in analyzers, each registered as a real entry point like any
  third-party plugin would be:
  - `syllables` -- per-word and per-line syllable counts.
  - `end_rhyme` -- end-of-line rhyme scheme detection (e.g. `AABB`).
  - `internal_rhyme` -- cross-line and multisyllabic internal rhyme chains.
  - `flow_pattern` -- ASCII stressed/unstressed rhythm notation per line.
- Rendering (`verseflow.render`): colored ANSI terminal output and a
  self-contained, dependency-free standalone HTML report with rhyme-chain
  highlighting and hover interactions.
- `verseflow` command-line interface (`analyze`, `demo`, `list-analyzers`)
  with `ascii` / `json` / `html` output formats.
- Full pytest suite covering phonetics, rhyme matching, all four
  analyzers, the plugin registry (including entry-point discovery and
  plugin-failure isolation), and the CLI.
- GitHub Actions CI (Python 3.10/3.11/3.12: ruff, mypy, pytest).
- Contributor documentation, issue/PR templates, and Contributor Covenant
  Code of Conduct.

[0.1.0]: https://github.com/AadiCodes4/verseflow/releases/tag/v0.1.0
