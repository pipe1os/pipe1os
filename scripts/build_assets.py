"""Generate the README's SVG assets with the brand fonts converted to outlines.

Fonts are Mona Sans (variable) and Monaspace Neon 400 as woff2, e.g. from the
portfolio build output (dist/_astro).

usage: uv run --no-project --with fonttools --with brotli --with uharfbuzz \
         python scripts/build_assets.py [out_dir] [fonts_dir]
"""
import io
import pathlib
import sys

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "assets")
FONTS = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else r"C:/Users/Pipe/Documents/Proyectos/Web/Astro/portfolio/dist/_astro")
MONA = next(FONTS.glob("mona-sans-latin-wdth-normal*.woff2"))
MONO = next(FONTS.glob("monaspace-neon-latin-400-normal*.woff2"))
OUT.mkdir(parents=True, exist_ok=True)

W = 846  # GitHub profile README content width at desktop


def num(n):
    return f"{n:.1f}".rstrip("0").rstrip(".")


class Face:
    def __init__(self, path, **axes):
        tt = TTFont(path)
        if axes:
            tt = instantiateVariableFont(tt, axes)
        tt.flavor = None
        buf = io.BytesIO()
        tt.save(buf)
        data = buf.getvalue()
        self.tt = TTFont(io.BytesIO(data))
        self.hb = hb.Font(hb.Face(data))
        self.upem = self.tt["head"].unitsPerEm
        self.gs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.cap = self.tt["OS/2"].sCapHeight / self.upem

    def _shape(self, text):
        b = hb.Buffer()
        b.add_str(text)
        b.guess_segment_properties()
        hb.shape(self.hb, b, {"kern": True})
        return b.glyph_infos, b.glyph_positions

    def width(self, text, size, track=0):
        _, pos = self._shape(text)
        return sum(p.x_advance for p in pos) * size / self.upem + track * size * (len(pos) - 1)

    def glyphs(self, text, size, x, y, track=0):
        """One path per glyph: [(d, x_start)]."""
        s = size / self.upem
        out = []
        for info, pos in zip(*self._shape(text)):
            pen = SVGPathPen(self.gs, ntos=num)
            t = (s, 0, 0, -s, x + pos.x_offset * s, y - pos.y_offset * s)
            self.gs[self.order[info.codepoint]].draw(TransformPen(pen, t))
            out.append((pen.getCommands(), x))
            x += pos.x_advance * s + track * size
        return out

    def path(self, text, size, x, y, track=0, anchor="start"):
        w = self.width(text, size, track)
        x -= {"start": 0, "middle": w / 2, "end": w}[anchor]
        return "".join(d for d, _ in self.glyphs(text, size, x, y, track)), w


display = Face(MONA, wdth=125, wght=760)
title = Face(MONA, wdth=112, wght=640)
body = Face(MONA, wdth=100, wght=430)
medium = Face(MONA, wdth=100, wght=520)
mono = Face(MONO)

THEMES = {
    "dark": dict(fg="#ecebe6", mute="#8f8e89", rule="#2c2c2d", line="#3a3a3b", plate="#0c0c0d", signal="#ff4f1f"),
    "light": dict(fg="#0c0c0d", mute="#63625e", rule="#d6d5cf", line="#c4c3bc", plate="#ecebe6", signal="#ff4f1f"),
}


def svg(w, h, body, label, style=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{num(h)}" '
        f'viewBox="0 0 {num(w)} {num(h)}" role="img" aria-label="{label}">'
        f"<title>{label}</title>{f'<style>{style}</style>' if style else ''}{body}</svg>\n"
    )


def write(name, content):
    (OUT / name).write_text(content, encoding="utf-8")


def caps(text, size, x, y, fill, anchor="start"):
    d, w = mono.path(text.upper(), size, x, y, track=0.08, anchor=anchor)
    return f'<path fill="{fill}" d="{d}"/>', w


# ---------- header ----------
HEADER_CSS = """
.g{animation:rise .9s cubic-bezier(.16,1,.3,1) backwards}
.pulse{transform-origin:center;transform-box:fill-box;animation:pulse 2.4s cubic-bezier(.2,.6,.3,1) infinite}
@keyframes rise{from{opacity:0;transform:translateY(22px)}}
@keyframes pulse{0%{opacity:.55;transform:scale(1)}70%,100%{opacity:0;transform:scale(3.2)}}
@media (prefers-reduced-motion:reduce){.g,.pulse{animation:none}.pulse{opacity:0}}
"""


def header(t):
    H, P = 372, 40
    parts = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{t["plate"]}" stroke="{t["rule"]}"/>']

    top = 58
    p, _ = caps("Full stack developer", 12, P, top, t["mute"])
    parts.append(p)
    p, w = caps("Open to work", 12, W - P, top, t["fg"], anchor="end")
    parts.append(p)
    cx, cy = W - P - w - 14, top - 4.5
    parts.append(f'<circle class="pulse" cx="{num(cx)}" cy="{num(cy)}" r="4" fill="{t["signal"]}"/>')
    parts.append(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="4" fill="{t["signal"]}"/>')

    size = 118
    lines = [("Felipe", 178), ("Arce", 280)]
    i = 0
    for text, base in lines:
        for d, _ in display.glyphs(text, size, P - 6, base, track=-0.02):
            parts.append(f'<path class="g" style="animation-delay:{i*45}ms" fill="{t["fg"]}" d="{d}"/>')
            i += 1
    arce_w = display.width("Arce", size, -0.02)
    dot = display.glyphs(".", size, P - 6 + arce_w - size * 0.02, 280)[0][0]
    parts.append(f'<path class="g" style="animation-delay:{i*45+120}ms" fill="{t["signal"]}" d="{dot}"/>')

    tag = ["I learn by building things", "that have to actually work."]
    for k, line in enumerate(tag):
        d, _ = body.path(line, 18, W - P, 252 + k * 27, anchor="end")
        parts.append(f'<path fill="{t["mute"]}" d="{d}"/>')

    parts.append(f'<path stroke="{t["rule"]}" d="M{P} 312.5H{W-P}"/>')
    base = 344
    cols = [("Concepción, Chile", P, "start"), ("36°49'S 73°03'W", W / 2, "middle"), ("pipeos.dev", W - P, "end")]
    for text, x, anchor in cols:
        p, _ = caps(text, 12, x, base, t["mute"], anchor)
        parts.append(p)
    return svg(W, H, "".join(parts), "Felipe Arce, full stack developer in Concepción, Chile. Open to work.", HEADER_CSS)


# ---------- section titles ----------
SECTIONS = {
    "oss": ("Contributed to", "Merged upstream"),
    "work": ("My work", "Built and maintained"),
    "stack": ("Stack", "What I use and what's next"),
    "activity": ("Activity", "Live from GitHub"),
}


def section(t, name, caption):
    H = 64
    d, _ = title.path(name, 26, 0, 38)
    c, _ = caps(caption, 11.5, W, 37, t["mute"], anchor="end")
    body_ = (
        f'<path fill="{t["fg"]}" d="{d}"/>{c}'
        f'<path stroke="{t["rule"]}" d="M0 55.5H{W}"/>'
        f'<path stroke="{t["signal"]}" stroke-width="2" d="M0 55.5H32"/>'
    )
    return svg(W, H, body_, name)


# ---------- link chips ----------
LINKS = {
    "portfolio": ("pipeos.dev", True),
    "linkedin": ("LinkedIn", False),
    "email": ("Email", False),
}


def chip(t, text, primary):
    H, PX, size, A = 40, 18, 13.5, 7
    tw = mono.width(text, size)
    w = tw + 10 + A + PX * 2
    d, _ = mono.path(text, size, PX, 25)
    ax, ay = PX + tw + 10, 15.5
    arrow = f"M{num(ax)} {num(ay+A)}L{num(ax+A)} {num(ay)}M{num(ax+1.5)} {num(ay)}H{num(ax+A)}V{num(ay+A-1.5)}"
    if primary:
        rect = f'<rect width="{num(w)}" height="{H}" rx="8" fill="{t["signal"]}"/>'
        fill = "#0c0c0d"
    else:
        rect = f'<rect x=".5" y=".5" width="{num(w-1)}" height="{H-1}" rx="7.5" fill="none" stroke="{t["line"]}"/>'
        fill = t["fg"]
    stroke = f'<path d="{arrow}" fill="none" stroke="{fill}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
    return svg(w, H, f'{rect}<path fill="{fill}" d="{d}"/>{stroke}', text)


# ---------- stack ----------
DAILY = [("TypeScript", "#3178c6"), ("React", "#61dafb"), ("Next.js", None), ("Astro", "#ff5a03"),
         ("Python", "#3572a5"), ("C++", "#f34b7d")]
LEARNING = [("Svelte", "#ff3e00"), ("Docker", "#2496ed"), ("AWS", "#ff9900"), ("Go", "#00add8"),
            ("PostgreSQL", "#336791")]


def stack(t):
    H, X0, size, gap = 82, 128, 17.5, 25
    parts = []
    for row, (label, items, learning) in enumerate([("Daily", DAILY, False), ("Learning", LEARNING, True)]):
        base = 24 + row * 46
        p, _ = caps(label, 11.5, 0, base - 1, t["mute"])
        parts.append(p)
        x = X0
        for name, color in items:
            color = color or t["fg"]
            cy = base - 6
            if learning:
                parts.append(f'<circle cx="{num(x+5)}" cy="{cy}" r="4.25" fill="none" stroke="{color}" stroke-width="1.5"/>')
            else:
                parts.append(f'<circle cx="{num(x+5)}" cy="{cy}" r="5" fill="{color}"/>')
            d, w = medium.path(name, size, x + 18, base)
            parts.append(f'<path fill="{t["fg"] if not learning else t["mute"]}" d="{d}"/>')
            x += 18 + w + gap
        assert x - gap <= W, f"{label} row overflows: {x - gap:.0f}px"
    return svg(W, H, "".join(parts), "Daily: " + ", ".join(n for n, _ in DAILY) + ". Learning: " + ", ".join(n for n, _ in LEARNING) + ".")


for mode, t in THEMES.items():
    write(f"header-{mode}.svg", header(t))
    write(f"stack-{mode}.svg", stack(t))
    for key, (name, caption) in SECTIONS.items():
        write(f"title-{key}-{mode}.svg", section(t, name, caption))
    for key, (text, primary) in LINKS.items():
        write(f"link-{key}-{mode}.svg", chip(t, text, primary))
write("gap.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="6" height="1"/>\n')

print("\n".join(f"{p.name} {p.stat().st_size//1024}KB" for p in sorted(OUT.glob("*.svg"))))
