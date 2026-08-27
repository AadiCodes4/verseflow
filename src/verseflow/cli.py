"""The ``verseflow`` command-line interface.

.. code-block:: text

    verseflow analyze poem.txt --format ascii
    verseflow analyze poem.txt --format json -o report.json
    verseflow analyze poem.txt --format html -o report.html
    verseflow demo --format ascii
    verseflow list-analyzers
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from verseflow import render
from verseflow.plugins import list_analyzers, run_pipeline

# A short, 100% original demo verse written for this project -- no lyrics
# from any real song or artist appear anywhere in verseflow. See
# CONTRIBUTING.md / README.md for more on this policy.
DEMO_VERSE = """\
Grinding through the midnight while the city lights stay low
Chasing bigger visions than the shadows used to throw
Every ounce of hustle turns my worries into gold
Still the fire in my spirit burning steady, burning bold
Steady on the pavement with my vision set on prize
Building up a future that no distance can disguise
Every word I'm speaking turns the struggle to design
Nothing but the grind and a clear mind until they align
"""


def _parse_analyzer_list(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    names = [name.strip() for name in raw.split(",") if name.strip()]
    return names or None


def _write_output(content: str, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        print(f"Wrote {output_path}", file=sys.stderr)
    else:
        print(content)


def _render(
    text: str,
    *,
    fmt: str,
    analyzer_names: list[str] | None,
    output_path: str | None,
) -> int:
    result = run_pipeline(text, analyzer_names)

    if fmt == "json":
        content = json.dumps(result.to_dict(), indent=2)
    elif fmt == "html":
        content = render.render_html(result)
    else:
        # Colored ANSI when writing straight to a terminal; plain when
        # redirected to a file, unless the user asked for a file via -o
        # (in which case colors would just be escape-code noise).
        color = None if output_path is None else False
        content = render.render_ascii(result, color=color)

    _write_output(content, output_path)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.exists():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    return _render(
        text,
        fmt=args.format,
        analyzer_names=_parse_analyzer_list(args.analyzers),
        output_path=args.output,
    )


def cmd_demo(args: argparse.Namespace) -> int:
    return _render(
        DEMO_VERSE,
        fmt=args.format,
        analyzer_names=_parse_analyzer_list(args.analyzers),
        output_path=args.output,
    )


def cmd_list_analyzers(args: argparse.Namespace) -> int:
    names = list_analyzers()
    if not names:
        print("No analyzers registered.")
        return 0
    print("Registered analyzers:")
    for name in names:
        print(f"  - {name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verseflow",
        description=(
            "Analyze rhyme scheme, internal rhyme chains, syllables, and flow in "
            "rap/R&B-style lyrics or any verse text."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    format_choices = ("ascii", "json", "html")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a text file of lyrics/verse.")
    analyze_parser.add_argument("file", help="Path to a UTF-8 text file (one line per lyric line).")
    analyze_parser.add_argument(
        "--format", choices=format_choices, default="ascii", help="Output format (default: ascii)."
    )
    analyze_parser.add_argument(
        "--analyzers",
        default=None,
        help="Comma-separated analyzer names to run (default: all registered analyzers).",
    )
    analyze_parser.add_argument(
        "-o", "--output", default=None, help="Write output to this file instead of stdout."
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    demo_parser = subparsers.add_parser(
        "demo", help="Run verseflow on a short, original built-in demo verse."
    )
    demo_parser.add_argument(
        "--format", choices=format_choices, default="ascii", help="Output format (default: ascii)."
    )
    demo_parser.add_argument(
        "--analyzers",
        default=None,
        help="Comma-separated analyzer names to run (default: all registered analyzers).",
    )
    demo_parser.add_argument(
        "-o", "--output", default=None, help="Write output to this file instead of stdout."
    )
    demo_parser.set_defaults(func=cmd_demo)

    list_parser = subparsers.add_parser(
        "list-analyzers", help="List all registered analyzers (built-in and plugin)."
    )
    list_parser.set_defaults(func=cmd_list_analyzers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
