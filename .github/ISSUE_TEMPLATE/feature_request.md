---
name: Feature request
about: Suggest an idea for verseflow
title: "[Feature] "
labels: enhancement
assignees: ""
---

**Is this a new analyzer, or a change to core/CLI/rendering?**
If it's a new analysis pass (e.g. a new rhyme/flow/phonetic metric),
consider whether it could be built as a third-party plugin via the
`verseflow.analyzers` entry-point group instead of a core change -- see
`CONTRIBUTING.md`. That said, proposals for genuinely core-worthy
analyzers are welcome too.

**What problem does this solve?**
A clear description of the use case this feature would enable.

**Describe the solution you'd like**
What you want to happen. If it's a new analyzer, sketch what its
`AnalysisResult.data` shape might look like.

**Describe alternatives you've considered**
Any alternative solutions or workarounds you've thought about.

**Additional context**
Anything else -- links, references, or examples (original text only,
please, no real song lyrics).
