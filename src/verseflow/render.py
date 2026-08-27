"""Rendering: colored ANSI terminal output and a self-contained HTML report.

Both renderers work purely off :class:`verseflow.plugins.PipelineResult`
(the merged output of ``end_rhyme``, ``internal_rhyme``, and whatever
other analyzers ran) plus the original lines -- they don't recompute any
phonetics themselves, so they display exactly what the pipeline produced,
including from third-party plugins.
"""

from __future__ import annotations

import html
import json
import os
import sys
from typing import Any

from verseflow import phonetics
from verseflow.plugins import PipelineResult

# A palette of visually distinct colors, reused (by index) for both the
# ANSI terminal renderer and the HTML renderer so a given rhyme
# group/chain reads as "the same color" whichever format you pick.
# (hex, ANSI-256 code) pairs.
PALETTE: list[tuple[str, int]] = [
    ("#e6194B", 196),  # red
    ("#3cb44b", 34),   # green
    ("#4363d8", 33),   # blue
    ("#f58231", 208),  # orange
    ("#911eb4", 129),  # purple
    ("#42d4f4", 51),   # cyan
    ("#f032e6", 201),  # magenta
    ("#bfef45", 190),  # lime
    ("#fabed4", 218),  # pink
    ("#469990", 30),   # teal
    ("#9A6324", 94),   # brown
    ("#808000", 100),  # olive
]


def _color_for(index: int) -> tuple[str, int]:
    return PALETTE[index % len(PALETTE)]


def _use_color(explicit: bool | None = None) -> bool:
    """Decide whether to emit ANSI escapes.

    Honors an explicit override, then the NO_COLOR convention
    (https://no-color.org/), then falls back to whether stdout looks like
    a terminal.
    """
    if explicit is not None:
        return explicit
    if os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stdout.isatty()


def _ansi(text: str, code: int, *, bold: bool = False) -> str:
    prefix = f"\x1b[{'1;' if bold else ''}38;5;{code}m"
    return f"{prefix}{text}\x1b[0m"


# --------------------------------------------------------------------------
# ANSI terminal rendering
# --------------------------------------------------------------------------


def render_ascii(result: PipelineResult, *, color: bool | None = None) -> str:
    """Render a full pipeline result as a terminal-friendly ASCII/ANSI report.

    Reconstructs the end-rhyme scheme and internal-rhyme chains with
    distinct colors (each rhyme group/chain gets its own color, reused
    consistently), and includes any other registered analyzer's plain
    summary text as-is. Colors are omitted automatically when stdout
    isn't a terminal or ``NO_COLOR`` is set, unless ``color`` overrides
    that.
    """
    use_color = _use_color(color)
    sections: list[str] = []

    end_rhyme = result.results.get("end_rhyme")
    internal_rhyme = result.results.get("internal_rhyme")

    if end_rhyme is not None:
        sections.append(_render_end_rhyme_section(end_rhyme.data, use_color))
    if internal_rhyme is not None:
        sections.append(_render_internal_rhyme_section(internal_rhyme.data, use_color))

    # Any other analyzer (built-in syllables/flow_pattern, or a
    # third-party plugin) just gets its own summary printed under a
    # header -- verseflow doesn't need to know anything about its
    # internals to render *something* useful.
    handled = {"end_rhyme", "internal_rhyme"}
    for name, analysis in result.results.items():
        if name in handled:
            continue
        header = f"== {name} ==" if not use_color else _ansi(f"== {name} ==", 15, bold=True)
        sections.append(f"{header}\n{analysis.summary}")

    return "\n\n".join(sections)


def _render_end_rhyme_section(data: dict[str, Any], use_color: bool) -> str:
    lines = data.get("lines", [])
    scheme = data.get("scheme", "")

    label_order: list[str] = []
    for entry in lines:
        label = entry.get("label")
        if label and label not in label_order:
            label_order.append(label)
    color_index = {label: i for i, label in enumerate(label_order)}

    header = "== end_rhyme ==" if not use_color else _ansi("== end_rhyme ==", 15, bold=True)
    out = [header]
    for entry in lines:
        label = entry["label"] or "?"
        rtype = entry["rhyme_type"] or "n/a"
        text = entry["text"]
        if use_color and entry["label"]:
            _, code = _color_for(color_index[entry["label"]])
            label_display = _ansi(f"[{label}]", code, bold=True)
        else:
            label_display = f"[{label}]"
        out.append(f"{label_display} ({rtype:>5})  {text}")

    scheme_display = scheme
    if use_color:
        scheme_display = "".join(
            _ansi(ch, _color_for(color_index[ch])[1], bold=True) if ch in color_index else ch
            for ch in scheme
        )
    out.append(f"\nScheme: {scheme_display}")
    return "\n".join(out)


def _render_internal_rhyme_section(data: dict[str, Any], use_color: bool) -> str:
    chains = data.get("chains", [])
    header = (
        "== internal_rhyme ==" if not use_color else _ansi("== internal_rhyme ==", 15, bold=True)
    )
    out = [header]
    if not chains:
        out.append("No internal rhyme chains found (2+ shared-rhyme words).")
        return "\n".join(out)

    for chain in chains:
        idx = chain["id"]
        if use_color:
            _, code = _color_for(idx)
            tag = _ansi(f"Chain {idx}", code, bold=True)
        else:
            tag = f"Chain {idx}"
        word_list = ", ".join(f"{m['word']} (line {m['line_no']})" for m in chain["words"])
        out.append(f"{tag} [{chain['rhyme_key']}]: {word_list}")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Self-contained HTML report
# --------------------------------------------------------------------------


def render_html(result: PipelineResult, *, title: str = "verseflow report") -> str:
    """Render a pipeline result as a single, dependency-free standalone HTML page.

    Everything (CSS, JavaScript, data) is inlined into one file -- no
    CDN, no external stylesheet, no build step. Opening the file directly
    in a browser highlights:

    * each line's end-rhyme group, in a distinct color per scheme letter;
    * every internal/multisyllabic rhyme chain, in a distinct color per
      chain, with hover-to-highlight across the whole document;

    with checkboxes to toggle each highlight layer independently, plus
    plain tables for syllable counts and flow patterns.
    """
    end_rhyme = result.results.get("end_rhyme")
    internal_rhyme = result.results.get("internal_rhyme")
    syllables = result.results.get("syllables")
    flow_pattern = result.results.get("flow_pattern")

    end_rhyme_line_list = end_rhyme.data.get("lines", []) if end_rhyme else []
    end_rhyme_lines = {e["line_no"]: e for e in end_rhyme_line_list}
    chains = internal_rhyme.data.get("chains", []) if internal_rhyme else []

    label_order: list[str] = []
    for entry in end_rhyme_lines.values():
        if entry["label"] and entry["label"] not in label_order:
            label_order.append(entry["label"])
    end_color = {label: _color_for(i)[0] for i, label in enumerate(label_order)}

    chain_color = {chain["id"]: _color_for(chain["id"])[0] for chain in chains}
    # occurrences indexed by (line_no, start) -> chain id, for quick lookup
    # while walking each line's word spans.
    chain_lookup: dict[tuple[int, int], int] = {}
    for chain in chains:
        for occ in chain["words"]:
            chain_lookup[(occ["line_no"], occ["start"])] = chain["id"]

    body_lines_html = []
    for line_no, line in enumerate(result.lines, start=1):
        spans = phonetics.iter_word_spans(line)
        end_entry = end_rhyme_lines.get(line_no)
        end_word_start = None
        if end_entry and spans and end_entry.get("end_word") is not None:
            end_word_start = spans[-1].start

        pieces = []
        cursor = 0
        for span in spans:
            if span.start > cursor:
                pieces.append(html.escape(line[cursor : span.start]))
            classes = ["word"]
            data_attrs = ""
            style = ""
            is_end = end_word_start is not None and span.start == end_word_start
            chain_id = chain_lookup.get((line_no, span.start))

            if is_end and end_entry is not None:
                classes.append("end-word")
                data_attrs += f' data-end-label="{html.escape(end_entry["label"] or "")}"'
                style += f"--end-color:{end_color.get(end_entry['label'], '#999')};"
            if chain_id is not None:
                classes.append("chain-word")
                data_attrs += f' data-chain="{chain_id}"'
                style += f"--chain-color:{chain_color.get(chain_id, '#999')};"

            pieces.append(
                f'<span class="{" ".join(classes)}"{data_attrs} style="{style}">'
                f"{html.escape(span.word)}</span>"
            )
            cursor = span.end
        if cursor < len(line):
            pieces.append(html.escape(line[cursor:]))

        scheme_label = end_entry["label"] if end_entry else None
        label_html = (
            f'<span class="line-label" style="color:{end_color.get(scheme_label, "#999")}">'
            f"{html.escape(scheme_label)}</span>"
            if scheme_label
            else '<span class="line-label muted">-</span>'
        )
        body_lines_html.append(
            f'<div class="lyric-line">{label_html}'
            f'<span class="line-text">{"".join(pieces)}</span></div>'
        )

    legend_end_html = "".join(
        f'<li><span class="swatch" style="background:{end_color[label]}"></span>'
        f"Group {html.escape(label)}</li>"
        for label in label_order
    )
    legend_chain_html = "".join(
        f'<li><span class="swatch" style="background:{chain_color[c["id"]]}"></span>'
        f'Chain {c["id"]} [{html.escape(c["rhyme_key"])}]: '
        f'{html.escape(", ".join(m["word"] for m in c["words"]))}</li>'
        for c in chains
    )

    syllables_rows = ""
    if syllables:
        for entry in syllables.data.get("lines", []):
            words_html = " ".join(
                f'{html.escape(w["word"])}<sub>{w["syllables"]}</sub>' for w in entry["words"]
            )
            syllables_rows += (
                f"<tr><td>{entry['line_no']}</td><td>{entry['syllables']}</td>"
                f"<td>{words_html}</td></tr>"
            )

    flow_rows = ""
    if flow_pattern:
        for entry in flow_pattern.data.get("lines", []):
            flow_rows += (
                f"<tr><td>{entry['line_no']}</td>"
                f'<td class="mono">{html.escape(entry["pattern_spaced"])}</td>'
                f"<td>{html.escape(entry['text'])}</td></tr>"
            )

    raw_json = json.dumps(result.to_dict(), indent=2)

    return _HTML_TEMPLATE.format(
        title=html.escape(title),
        body_lines="\n".join(body_lines_html),
        legend_end=legend_end_html or "<li>(no end-rhyme data)</li>",
        legend_chain=legend_chain_html or "<li>(no internal rhyme chains found)</li>",
        syllables_rows=syllables_rows,
        flow_rows=flow_rows,
        raw_json=html.escape(raw_json),
    )


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    color-scheme: light dark;
    --bg: #0f1115;
    --panel: #171a21;
    --text: #e8e8ec;
    --muted: #8b8f9a;
    --border: #2a2e38;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2rem 1rem 4rem;
    background: var(--bg); color: var(--text);
    font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5;
  }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.25rem; }}
  .subtitle {{ color: var(--muted); margin-top: 0; margin-bottom: 1.5rem; font-size: 0.9rem; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  .panel {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
  }}
  .panel h2 {{ margin-top: 0; font-size: 1.05rem; }}
  .controls {{
    display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 0.5rem; font-size: 0.9rem;
  }}
  .controls label {{ cursor: pointer; user-select: none; }}
  .lyric-line {{
    display: flex; align-items: baseline; gap: 0.75rem;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 1.02rem; padding: 0.15rem 0;
  }}
  .line-label {{
    display: inline-block; width: 1.6rem; text-align: center;
    font-weight: 700; flex-shrink: 0;
  }}
  .line-label.muted {{ color: var(--muted); }}
  .word {{ padding: 0.05rem 0.15rem; border-radius: 4px; transition: outline 0.1s ease; }}
  .end-word {{ background: color-mix(in srgb, var(--end-color) 35%, transparent); }}
  .chain-word {{ box-shadow: inset 0 -3px 0 0 var(--chain-color); }}
  .chain-word.end-word {{
    background: color-mix(in srgb, var(--end-color) 35%, transparent);
    box-shadow: inset 0 -3px 0 0 var(--chain-color);
  }}
  body.hide-end .end-word {{ background: none !important; }}
  body.hide-chain .chain-word {{ box-shadow: none !important; }}
  .word.chain-hover {{ outline: 2px solid #fff; outline-offset: 1px; }}
  ul.legend {{ list-style: none; padding: 0; margin: 0.5rem 0 0; font-size: 0.9rem; }}
  ul.legend li {{ padding: 0.15rem 0; }}
  .swatch {{
    display: inline-block; width: 0.85rem; height: 0.85rem; border-radius: 3px;
    margin-right: 0.5rem; vertical-align: middle;
  }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  th, td {{ text-align: left; padding: 0.35rem 0.6rem; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; }}
  td.mono {{ font-family: Consolas, Menlo, monospace; }}
  details summary {{ cursor: pointer; color: var(--muted); }}
  pre {{
    background: #0b0d11; border: 1px solid var(--border); border-radius: 8px;
    padding: 1rem; overflow-x: auto; font-size: 0.8rem;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg: #f7f7fa; --panel: #ffffff; --text: #1b1d23; --muted: #6b7280; --border: #e2e4ea;
    }}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>verseflow report</h1>
  <p class="subtitle">
    Rhyme scheme, internal rhyme chains, syllables, and flow -- generated by verseflow.
  </p>

  <div class="panel">
    <h2>Lyrics</h2>
    <div class="controls">
      <label><input type="checkbox" id="toggle-end" checked> End-rhyme highlighting</label>
      <label><input type="checkbox" id="toggle-chain" checked> Internal rhyme chains</label>
    </div>
    {body_lines}
  </div>

  <div class="panel">
    <h2>End-rhyme groups</h2>
    <ul class="legend">{legend_end}</ul>
  </div>

  <div class="panel">
    <h2>Internal rhyme chains</h2>
    <p class="subtitle" style="margin-top:-0.25rem;">
      Hover a highlighted word to see the rest of its chain light up.
    </p>
    <ul class="legend">{legend_chain}</ul>
  </div>

  <div class="panel">
    <h2>Syllables</h2>
    <table>
      <thead><tr><th>Line</th><th>Total</th><th>Per word</th></tr></thead>
      <tbody>{syllables_rows}</tbody>
    </table>
  </div>

  <div class="panel">
    <h2>Flow pattern</h2>
    <table>
      <thead><tr><th>Line</th><th>Pattern (x = stressed)</th><th>Text</th></tr></thead>
      <tbody>{flow_rows}</tbody>
    </table>
  </div>

  <div class="panel">
    <details>
      <summary>Raw JSON</summary>
      <pre>{raw_json}</pre>
    </details>
  </div>
</div>
<script>
(function () {{
  var toggleEnd = document.getElementById('toggle-end');
  var toggleChain = document.getElementById('toggle-chain');

  function sync() {{
    document.body.classList.toggle('hide-end', !toggleEnd.checked);
    document.body.classList.toggle('hide-chain', !toggleChain.checked);
  }}
  toggleEnd.addEventListener('change', sync);
  toggleChain.addEventListener('change', sync);
  sync();

  document.querySelectorAll('[data-chain]').forEach(function (el) {{
    el.addEventListener('mouseenter', function () {{
      var id = el.getAttribute('data-chain');
      document.querySelectorAll('[data-chain="' + id + '"]').forEach(function (peer) {{
        peer.classList.add('chain-hover');
      }});
    }});
    el.addEventListener('mouseleave', function () {{
      var id = el.getAttribute('data-chain');
      document.querySelectorAll('[data-chain="' + id + '"]').forEach(function (peer) {{
        peer.classList.remove('chain-hover');
      }});
    }});
  }});
}})();
</script>
</body>
</html>
"""
