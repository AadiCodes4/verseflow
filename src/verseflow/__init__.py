"""verseflow: a plugin-extensible rap/R&B lyric flow & rhyme analysis toolkit.

Public API re-exports for convenience:

>>> from verseflow import run_pipeline
>>> result = run_pipeline("cat in a hat\\nsat right there")
>>> sorted(result.results)
['end_rhyme', 'flow_pattern', 'internal_rhyme', 'syllables']
"""

from __future__ import annotations

from verseflow.plugins import (
    PipelineResult,
    get_analyzer,
    list_analyzers,
    register_analyzer,
    run_pipeline,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "PipelineResult",
    "get_analyzer",
    "list_analyzers",
    "register_analyzer",
    "run_pipeline",
]
