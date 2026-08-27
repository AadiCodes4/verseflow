---
name: Bug report
about: Report something that doesn't work the way it should
title: "[Bug] "
labels: bug
assignees: ""
---

**Describe the bug**
A clear, concise description of what's wrong.

**To reproduce**
Steps to reproduce, ideally including the exact input verse/lines and the
command you ran, e.g.:

```bash
verseflow analyze my-verse.txt --format ascii
```

```text
paste the input lines here (original text only, please -- see note below)
```

**Expected behavior**
What you expected verseflow to output instead.

**Actual output**
```text
paste the actual output here
```

**Environment**
- verseflow version: `python -c "import verseflow; print(verseflow.__version__)"`
- Python version: `python --version`
- OS:

**Additional context**
Anything else that might help (e.g. specific words whose phonetics/rhyme
detection looked wrong, and why you believe that -- a CMUdict
pronunciation reference is great if you have one).

---

> **Please don't include real song lyrics** in bug reports -- use a short
> made-up example instead. See `CONTRIBUTING.md` for why.
