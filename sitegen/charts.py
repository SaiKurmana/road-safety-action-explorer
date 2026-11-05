"""Tiny dependency-free SVG charts for the static site, themed with CSS custom properties.

Colors come from CSS variables (--series-1 state, --series-2 U.S., --series-3 peers, --median),
so light/dark mode swap in style.css. Every chart is paired with a data table on the page, and
markers carry <title> tooltips for hover.
"""

from __future__ import annotations

import math
from html import escape


def _nice_max(v: float) -> float:
    """Smallest 'nice' axis maximum (5 gridline steps of 1, 2, 2.5, or 5 x 10^k) that covers v."""
    if v <= 0:
        return 1.0
    raw = v / 5
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    return step * 5


def line_chart(years: list[int], series: list[tuple[str, str, list[float]]], y_label: str, digits: int = 1) -> str:
    """series: (name, css_var, values aligned with years). One y-axis, starting at zero."""
    w, h, ml, mr, mt, mb = 640, 280, 44, 110, 14, 34
    pw, ph = w - ml - mr, h - mt - mb
    ymax = _nice_max(max(v for _, _, vals in series for v in vals if v is not None))
    n = len(years)

    def x(i: int) -> float:
        return ml + (pw * i / (n - 1) if n > 1 else pw / 2)

    def y(v: float) -> float:
        return mt + ph - ph * v / ymax

    parts = [
        f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(y_label)} by year">',
    ]
    for k in range(6):
        v = ymax * k / 5
        parts.append(f'<line class="grid" x1="{ml}" x2="{ml + pw}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        parts.append(f'<text class="tick" x="{ml - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:g}</text>')
    for i, yr in enumerate(years):
        parts.append(f'<text class="tick" x="{x(i):.1f}" y="{h - 12}" text-anchor="middle">{yr}</text>')
    for name, var, vals in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        parts.append(f'<polyline class="line" style="stroke:var({var})" points="{pts}"/>')
        for i, v in enumerate(vals):
            if v is None:
                continue
            parts.append(
                f'<circle class="pt" style="fill:var({var})" cx="{x(i):.1f}" cy="{y(v):.1f}" r="4">'
                f"<title>{escape(name)}, {years[i]}: {v:.{digits}f}</title></circle>"
            )
    # Direct labels at line ends, nudged apart if they collide.
    ends = sorted(((y(vals[-1]), name) for name, _, vals in series if vals[-1] is not None), key=lambda t: t[0])
    last = -1e9
    for yy, name in ends:
        yy = max(yy, last + 14)
        last = yy
        parts.append(f'<text class="dlabel" x="{x(n - 1) + 8:.1f}" y="{yy + 4:.1f}">{escape(name)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def dot_chart(rows: list[dict], keys: list[tuple[str, str, str, str]], x_label: str) -> str:
    """Comparison dot plot. rows: {label, <key>: value}; keys: (key, name, css_var, shape)."""
    ml, mr, mt, rowh = 210, 24, 34, 30
    w = 720
    pw = w - ml - mr
    h = mt + rowh * len(rows) + 34
    xmax = _nice_max(max((r[k] for r in rows for k, *_ in keys if r.get(k) is not None), default=1))

    def x(v: float) -> float:
        return ml + pw * v / xmax

    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(x_label)} comparison">']
    lx = ml
    for _, name, var, shape in keys:
        parts.append(_marker(shape, lx + 6, 12, var, ""))
        parts.append(f'<text class="legend" x="{lx + 16}" y="16">{escape(name)}</text>')
        lx += 36 + 7 * len(name)
    for k in range(6):
        v = xmax * k / 5
        parts.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{mt}" y2="{h - 30}"/>')
        parts.append(f'<text class="tick" x="{x(v):.1f}" y="{h - 16}" text-anchor="middle">{v:g}</text>')
    for i, r in enumerate(rows):
        cy = mt + rowh * i + rowh / 2
        parts.append(
            f'<text class="rowlabel" x="{ml - 8}" y="{cy + 4:.1f}" text-anchor="end">{escape(r["label"])}</text>'
        )
        for key, name, var, shape in keys:
            v = r.get(key)
            if v is None:
                continue
            parts.append(_marker(shape, x(v), cy, var, f"{name}: {v:.2f}"))
    parts.append(f'<text class="tick" x="{ml + pw / 2:.1f}" y="{h - 2}" text-anchor="middle">{escape(x_label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _marker(shape: str, cx: float, cy: float, var: str, tip: str) -> str:
    t = f"<title>{escape(tip)}</title>" if tip else ""
    style = f"fill:var({var});stroke:var(--surface-1)"
    if shape == "circle":
        return f'<circle class="mk" style="{style}" cx="{cx:.1f}" cy="{cy:.1f}" r="6">{t}</circle>'
    if shape == "diamond":
        d = 6
        return (
            f'<polygon class="mk" style="{style}" points="{cx:.1f},{cy - d:.1f} {cx + d:.1f},{cy:.1f} '
            f'{cx:.1f},{cy + d:.1f} {cx - d:.1f},{cy:.1f}">{t}</polygon>'
        )
    if shape == "square":
        return f'<rect class="mk" style="{style}" x="{cx - 5:.1f}" y="{cy - 5:.1f}" width="10" height="10" rx="2">{t}</rect>'
    return (
        f'<rect class="mk" style="fill:var({var})" x="{cx - 1.5:.1f}" y="{cy - 8:.1f}" width="3" height="16" '
        f'rx="1">{t}</rect>'
    )
