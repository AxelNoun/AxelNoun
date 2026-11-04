"""Animated SVGs for the profile README: neuroscience, neuromorphic, AI.

Run:  python3 tools/make_animations.py   (writes into ../assets)
CSS animations + SMIL only: no script, no external resource (GitHub-safe).
"""
from __future__ import annotations

import math
import os
import random

from make_assets import MONO, OUT, SANS, THEMES, esc


def svg_open(W, H, label):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(label)}">']


def smil_cycle(dur, begin):
    return f'dur="{dur:.3f}s" begin="{begin:.3f}s" repeatCount="indefinite"'


def kt(*xs):
    """keyTimes string, clamped to be strictly increasing within [0,1]."""
    out, last = [], -1.0
    for x in xs:
        x = min(1.0, max(0.0, x))
        if x <= last:
            x = min(1.0, last + 0.001)
        out.append(x)
        last = x
    out[0], out[-1] = 0.0, 1.0
    return ";".join(f"{v:.4f}" for v in out)


# ===================================================================== triptych
def triptych(th: str) -> str:
    c = THEMES[th]
    W, H = 1280, 430
    pw, gap = 413, 20
    o = svg_open(W, H, "Three animated panels: a Neuropixels probe recording spikes; a neuromorphic chip whose cores wake only when a spike event arrives; a mixture-of-experts router sending tokens to experts.")
    o.append(f"""<defs><clipPath id="trc"><rect x="112" y="84" width="276" height="270"/></clipPath>
<radialGradient id="glow"><stop offset="0" stop-color="{c['hi']}" stop-opacity=".9"/><stop offset="1" stop-color="{c['hi']}" stop-opacity="0"/></radialGradient></defs>
<style>
.site{{fill:{c['faint']};opacity:.55}}
.sf{{fill:{c['hi']};opacity:0;animation:sf 2.6s linear infinite}}
@keyframes sf{{0%{{opacity:1}}12%{{opacity:0}}100%{{opacity:0}}}}
.ng{{opacity:0;animation:sf 2.6s linear infinite}}
.tr{{fill:none;stroke:{c['acc']};stroke-width:1.5;stroke-linejoin:round}}
.scroll{{animation:scr 6s linear infinite}}
@keyframes scr{{from{{transform:translateX(0)}}to{{transform:translateX(-276px)}}}}
.cell{{animation:cf 3.4s ease-in-out infinite}}
@keyframes cf{{0%,100%{{opacity:.25}}8%{{opacity:1}}30%{{opacity:.25}}}}
.lbl{{font-family:{MONO};font-size:13px;fill:{c['faint']}}}
</style>""")
    for i in range(3):
        x = i * (pw + gap)
        o.append(f'<rect x="{x+.5}" y=".5" width="{pw-1}" height="{H-1}" rx="16" fill="{c["panel"]}" stroke="{c["border"]}"/>')
    heads = [("NEUROSCIENCE", "Listening to neurons", "// extracellular spikes, channel by channel"),
             ("NEUROMORPHIC", "Compute only on events", "// cores stay idle until a spike arrives"),
             ("AI", "Route tokens, sort by expert", "// grouped by expert: one matmul each")]
    for i, (tag, sub, cap) in enumerate(heads):
        x = i * (pw + gap)
        o.append(f'<text x="{x+26}" y="38" font-family="{MONO}" font-size="13" letter-spacing="2" fill="{c["acc"]}">{tag}</text>')
        o.append(f'<text x="{x+26}" y="64" font-family="{SANS}" font-size="21" font-weight="600" fill="{c["fg"]}">{esc(sub)}</text>')
        o.append(f'<text x="{x+26}" y="{H-24}" class="lbl">{esc(cap)}</text>')

    # ---------------- panel A: Neuropixels probe
    rng = random.Random(21)
    o.append('<g>')
    # two pyramidal neurons, left of the shank
    for (nx, ny, dl) in [(34, 168, 0.4), (30, 286, 1.7)]:
        o.append(f'<g stroke="{c["faint"]}" stroke-width="1.4" fill="none" opacity=".8">'
                 f'<path d="M{nx},{ny-9} L{nx},{ny-44} M{nx},{ny-30} l-10,-12 M{nx},{ny-24} l9,-10 M{nx-7},{ny+6} l-12,10 M{nx+7},{ny+6} l14,8 M{nx},{ny+8} l0,16"/></g>')
        o.append(f'<path d="M{nx-8},{ny+7} L{nx},{ny-10} L{nx+8},{ny+7} Z" fill="{c["acc2"]}"/>')
        o.append(f'<circle cx="{nx}" cy="{ny}" r="16" fill="url(#glow)" class="ng" style="animation-delay:{dl-2.6:.2f}s"/>')
    o.append(f'<path d="M58,82 L86,82 L86,328 L72,374 L58,328 Z" fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1.5"/>')
    sites = []
    for r in range(17):
        for col in (63, 75):
            y = 92 + r * 14
            sites.append((col, y))
            o.append(f'<rect class="site" x="{col}" y="{y}" width="6" height="6" rx="1"/>')
    for k in range(22):
        sx, sy = rng.choice(sites)
        o.append(f'<rect class="sf" x="{sx}" y="{sy}" width="6" height="6" rx="1" style="animation-delay:{-rng.uniform(0, 2.6):.2f}s"/>')
    # channel traces, scrolling
    o.append('<g clip-path="url(#trc)"><g class="scroll">')
    chans = [112, 154, 196, 238, 280, 322]
    for ci, y0 in enumerate(chans):
        pat = []
        spikes = sorted(rng.uniform(10, 260) for _ in range(rng.randint(2, 4)))
        xx = 0.0
        while xx < 276:
            v = rng.gauss(0, 1.1)
            for s in spikes:
                dx = xx - s
                if 0 <= dx < 3:
                    v = -16 * (dx / 3) if dx < 1.5 else -16 + (dx - 1.5) / 1.5 * 22
                elif 3 <= dx < 9:
                    v = 6 * (1 - (dx - 3) / 6)
            pat.append((xx, v))
            xx += 1.5
        pts = [(112 + x, y0 + v) for x, v in pat] + [(112 + 276 + x, y0 + v) for x, v in pat]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        o.append(f'<path class="tr" d="{d}" opacity="{.95 - ci*0.07:.2f}"/>')
    o.append('</g></g>')
    for ci, y0 in enumerate(chans):
        sx, sy = sites[4 + ci * 5]
        o.append(f'<path d="M{sx+6},{sy+3} C98,{sy+3} 100,{y0} 112,{y0}" fill="none" stroke="{c["faint"]}" stroke-dasharray="2 3" opacity=".5"/>')
    o.append(f'<line x1="388" x2="388" y1="84" y2="354" stroke="{c["hi"]}" stroke-width="1" opacity=".55"/>')
    o.append('</g>')

    # ---------------- panel B: neuromorphic chip (SMIL events)
    bx = pw + gap
    rng = random.Random(5)
    P = 4.8
    o.append(f'<g transform="translate({bx},0)">')
    cx0, cy0, cs, cg = 96, 104, 46, 14
    o.append(f'<rect x="78" y="86" width="258" height="258" rx="14" fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1.5"/>')
    for k in range(8):
        t = 102 + k * 30
        o.append(f'<path d="M{t},86 v-9 M{t},344 v9 M78,{t} h-9 M336,{t} h9" stroke="{c["faint"]}" stroke-width="2" opacity=".6"/>')
    def ctr(i, j):
        return cx0 + i * (cs + cg) + cs / 2, cy0 + j * (cs + cg) + cs / 2
    for i in range(4):
        for j in range(4):
            x, y = ctr(i, j)
            if i < 3:
                o.append(f'<line x1="{x+cs/2}" y1="{y}" x2="{x+cs/2+cg}" y2="{y}" stroke="{c["border"]}" stroke-width="3"/>')
            if j < 3:
                o.append(f'<line x1="{x}" y1="{y+cs/2}" x2="{x}" y2="{y+cs/2+cg}" stroke="{c["border"]}" stroke-width="3"/>')
    for i in range(4):
        for j in range(4):
            x, y = ctr(i, j)
            o.append(f'<rect x="{x-cs/2}" y="{y-cs/2}" width="{cs}" height="{cs}" rx="7" fill="{c["panel"]}" stroke="{c["border"]}"/>')
            for a in range(3):
                for b in range(3):
                    o.append(f'<circle cx="{x-10+a*10}" cy="{y-10+b*10}" r="1.6" fill="{c["faint"]}" opacity=".6"/>')
    # events
    flashes = []
    for e in range(12):
        si, sj = rng.randrange(4), rng.randrange(4)
        di, dj = rng.randrange(4), rng.randrange(4)
        if (si, sj) == (di, dj):
            di = (di + 2) % 4
        x1, y1 = ctr(si, sj)
        x2, y2 = ctr(di, dj)
        path = f"M{x1},{y1} L{x2},{y1} L{x2},{y2}"
        L = abs(x2 - x1) + abs(y2 - y1)
        f = min(0.6, L / 150 / P)
        b = rng.uniform(0, P)
        o.append(f'<circle r="4" fill="{c["hi"]}" opacity="0"><animateMotion path="{path}" {smil_cycle(P, b)} keyPoints="0;1;1" keyTimes="{kt(0, f, 1)}" calcMode="linear"/>'
                 f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="{kt(0, .01, f, f + .01, 1)}" {smil_cycle(P, b)}/></circle>')
        flashes.append((si, sj, b, 0.0))
        flashes.append((di, dj, b, f))
    for (i, j, b, f) in flashes:
        x, y = ctr(i, j)
        strong = f > 0
        o.append(f'<rect x="{x-cs/2}" y="{y-cs/2}" width="{cs}" height="{cs}" rx="7" fill="{c["hi"] if strong else c["acc"]}" opacity="0">'
                 f'<animate attributeName="opacity" values="0;0;{.75 if strong else .45};0;0" keyTimes="{kt(0, f, f + .006, f + .14, 1)}" {smil_cycle(P, b)}/></rect>')
    o.append('</g>')

    # ---------------- panel C: mixture-of-experts routing (SMIL)
    cxp = 2 * (pw + gap)
    rng = random.Random(9)
    P = 6.0
    o.append(f'<g transform="translate({cxp},0)">')
    words = ["neurons", "fire", "only", "when", "input", "crosses", "the", "threshold"]
    ecol = [c["vir"][0] if th == "light" else "#7B5EA7", c["vir"][1] if th == "light" else "#5B7BD5", c["vir"][2], c["vir"][3]]
    experts = [rng.randrange(4) for _ in words]
    tx, ty0, tstep = 26, 92, 33
    rx_, ry_ = 178, 220
    ex, ey0, estep = 300, 102, 62
    o.append(f'<rect x="{rx_-28}" y="{ry_-62}" width="56" height="124" rx="12" fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1.5"/>')
    o.append(f'<text x="{rx_}" y="{ry_+4}" text-anchor="middle" transform="rotate(-90 {rx_} {ry_})" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{c["muted"]}">ROUTER</text>')
    for k in range(4):
        y = ey0 + k * estep
        o.append(f'<rect x="{ex}" y="{y}" width="86" height="44" rx="9" fill="{c["bg"]}" stroke="{ecol[k]}" stroke-width="1.6"/>')
        o.append(f'<text x="{ex+14}" y="{y+27}" font-family="{MONO}" font-size="13" fill="{c["fg"]}">E{k}</text>')
        n = experts.count(k)
        for q in range(n):
            o.append(f'<rect x="{ex+42+q*9}" y="{y+15}" width="6" height="14" rx="2" fill="{ecol[k]}" opacity=".85"/>')
    for i, w in enumerate(words):
        y = ty0 + i * tstep
        e = experts[i]
        wlen = 14 + len(w) * 7.4
        o.append(f'<rect x="{tx}" y="{y}" width="{wlen:.0f}" height="24" rx="6" fill="{c["bg"]}" stroke="{c["border"]}"/>')
        o.append(f'<text x="{tx+7}" y="{y+16.5}" font-family="{MONO}" font-size="12" fill="{c["muted"]}">{w}</text>')
        sx, sy = tx + wlen, y + 12
        tyy = ey0 + e * estep + 22
        path = f"M{sx:.0f},{sy} C{sx+30:.0f},{sy} {rx_-50},{ry_} {rx_},{ry_} C{rx_+60},{ry_} {ex-50},{tyy} {ex},{tyy}"
        b = i * 0.42
        f = 0.36
        o.append(f'<path d="{path}" fill="none" stroke="{ecol[e]}" stroke-width="1" opacity=".18"/>')
        o.append(f'<circle r="4.5" fill="{ecol[e]}" opacity="0"><animateMotion path="{path}" {smil_cycle(P, b)} keyPoints="0;1;1" keyTimes="{kt(0, f, 1)}" calcMode="spline" keySplines=".4 0 .6 1;0 0 1 1"/>'
                 f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="{kt(0, .01, f, f + .01, 1)}" {smil_cycle(P, b)}/></circle>')
        o.append(f'<rect x="{tx}" y="{y}" width="{wlen:.0f}" height="24" rx="6" fill="none" stroke="{ecol[e]}" stroke-width="2" opacity="0">'
                 f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="{kt(0, .01, .12, 1)}" {smil_cycle(P, b)}/></rect>')
        ty = ey0 + e * estep
        o.append(f'<rect x="{ex}" y="{ty}" width="86" height="44" rx="9" fill="{ecol[e]}" opacity="0">'
                 f'<animate attributeName="opacity" values="0;0;.45;0;0" keyTimes="{kt(0, f, f + .006, f + .12, 1)}" {smil_cycle(P, b)}/></rect>')
    o.append('</g>')
    o.append('</svg>')
    return "\n".join(o)


# ===================================================================== myelinated axon divider
def axon(th: str) -> str:
    c = THEMES[th]
    W, H = 1280, 84
    y = 42
    P = 3.6
    o = svg_open(W, H, "A myelinated axon: the action potential jumps from one node of Ranvier to the next.")
    o.append(f"""<defs><radialGradient id="ag"><stop offset="0" stop-color="{c['hi']}" stop-opacity="1"/><stop offset=".45" stop-color="{c['hi']}" stop-opacity=".45"/><stop offset="1" stop-color="{c['hi']}" stop-opacity="0"/></radialGradient></defs>
<style>.ap{{opacity:0;animation:ap {P}s linear infinite}}
@keyframes ap{{0%{{opacity:1}}7%{{opacity:.15}}13%{{opacity:0}}100%{{opacity:0}}}}
.my{{fill:{c['panel']};stroke:{c['border']};stroke-width:1.3}}
@media (prefers-reduced-motion: reduce){{.ap{{animation:none}}}}</style>""")
    # soma + dendrites
    o.append(f'<g stroke="{c["faint"]}" stroke-width="1.6" fill="none" stroke-linecap="round">'
             f'<path d="M30,{y-6} l-14,-14 m6,6 l-10,2 M30,{y+6} l-16,14 m8,-8 l-4,10 M24,{y} l-18,-2"/></g>')
    o.append(f'<circle cx="38" cy="{y}" r="11" fill="{c["acc2"]}"/>')
    o.append(f'<circle cx="38" cy="{y}" r="20" fill="url(#ag)" class="ap" style="animation-delay:0s"/>')
    x_start, x_end = 56, 1188
    o.append(f'<line x1="{x_start-8}" y1="{y}" x2="{x_end}" y2="{y}" stroke="{c["faint"]}" stroke-width="2"/>')
    nodes = []
    sheath, node_gap = 104, 14
    x = x_start
    while x + sheath < x_end:
        o.append(f'<rect class="my" x="{x}" y="{y-8}" width="{sheath}" height="16" rx="8"/>')
        x += sheath
        nodes.append(x + node_gap / 2)
        x += node_gap
    step = 0.17
    for k, nx in enumerate(nodes):
        o.append(f'<circle cx="{nx:.1f}" cy="{y}" r="3" fill="{c["acc"]}"/>')
        o.append(f'<circle cx="{nx:.1f}" cy="{y}" r="15" fill="url(#ag)" class="ap" style="animation-delay:{(k+1)*step - P:.3f}s"/>')
    # terminals
    t0 = x_end
    o.append(f'<g stroke="{c["faint"]}" stroke-width="1.6" fill="none" stroke-linecap="round"><path d="M{t0},{y} C{t0+30},{y} {t0+40},{y-20} {t0+66},{y-22} M{t0},{y} L{t0+70},{y} M{t0},{y} C{t0+30},{y} {t0+40},{y+20} {t0+66},{y+22}"/></g>')
    td = (len(nodes) + 1) * step
    for dy in (-22, 0, 22):
        o.append(f'<circle cx="{t0+72}" cy="{y+dy}" r="5" fill="{c["acc"]}"/>')
        o.append(f'<circle cx="{t0+72}" cy="{y+dy}" r="13" fill="url(#ag)" class="ap" style="animation-delay:{td - P:.3f}s"/>')
    o.append('</svg>')
    return "\n".join(o)


# ===================================================================== terminal
def terminal() -> str:
    W, H = 1280, 384
    bg, fg, mut, red, grn, hi = "#0B0F14", "#E6EDF3", "#6E7681", "#FF7B72", "#3FB950", "#FDE725"
    cw = 11.5  # approx glyph advance at 19px monospace
    lines = [
        # (segments [(text,color)], kind: 'cmd' typed / 'out' instant)
        ([("$ ", grn), ("pytest -q tests/test_regression.py", fg), ("   # 1. reproduce the bug first", mut)], "cmd"),
        ([("F", red), ("  1 failed: assert simulated == expected", red)], "out"),
        ([("$ ", grn), ("git apply smallest-possible-fix.patch", fg), ("   # 2. fix only what is broken", mut)], "cmd"),
        ([("$ ", grn), ("pytest -q", fg), ("   # 3. nothing else breaks", mut)], "cmd"),
        ([("........................................................", grn), ("  all passed", grn)], "out"),
        ([("$ ", grn), ("gh pr create --fill", fg), ("   # 4. explain it upstream, follow the review", mut)], "cmd"),
        ([("✓ ", grn), ("merged by the maintainers", grn)], "out"),
    ]
    P = 15.0
    t = 0.6
    o = svg_open(W, H, "An animated terminal: reproduce the bug with a failing test, apply the smallest fix, run the whole suite, open the pull request, get it merged.")
    styles = [f".cv{{fill:{bg}}}", f".cur{{fill:{hi};animation:bl 1s steps(1) infinite}}@keyframes bl{{50%{{opacity:0}}}}",
              f".all{{animation:fo {P}s linear infinite}}@keyframes fo{{0%,94%{{opacity:1}}98%,100%{{opacity:0}}}}"]
    body = []
    x0, y0, lh = 34, 90, 37
    for i, (segs, kind) in enumerate(lines):
        y = y0 + i * lh
        full = "".join(s for s, _ in segs)
        n = len(full)
        dur = n * 0.032 if kind == "cmd" else 0.05
        if kind == "cmd":
            t += 0.5
        a, b2 = t / P * 100, (t + dur) / P * 100
        Wl = n * cw + 20
        styles.append(f".c{i}{{animation:k{i} {P}s infinite}}@keyframes k{i}{{0%{{transform:translateX(0)}}{a:.2f}%{{transform:translateX(0);animation-timing-function:steps({max(1, n)},end)}}{b2:.2f}%,100%{{transform:translateX({Wl:.0f}px)}}}}")
        tspans = "".join(f'<tspan fill="{col}">{esc(s)}</tspan>' for s, col in segs)
        body.append(f'<text x="{x0}" y="{y}" font-family="{MONO}" font-size="19" xml:space="preserve">{tspans}</text>')
        body.append(f'<rect class="cv c{i}" x="{x0-2}" y="{y-25}" width="{Wl:.0f}" height="34"/>')
        t += dur + (0.9 if kind == "out" else 0.35)
    yc = y0 + len(lines) * lh
    o.append("<style>" + "\n".join(styles) + "</style>")
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="{bg}" stroke="#30363D"/>')
    o.append(f'<path d="M1,40 H{W-1}" stroke="#21262D"/>')
    for k, col in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        o.append(f'<circle cx="{26+k*20}" cy="20" r="6" fill="{col}"/>')
    o.append(f'<text x="{W/2}" y="25" text-anchor="middle" font-family="{MONO}" font-size="14" fill="{mut}">how a fix reaches upstream — the order never changes</text>')
    o.append(f'<clipPath id="win"><rect x="2" y="42" width="{W-4}" height="{H-44}"/></clipPath>')
    o.append('<g clip-path="url(#win)"><g class="all">' + "\n".join(body) + "</g></g>")
    o.append(f'<text x="{x0}" y="{yc}" font-family="{MONO}" font-size="19" fill="{grn}">$ </text><rect class="cur" x="{x0+25}" y="{yc-18}" width="11" height="22"/>')
    o.append("</svg>")
    return "\n".join(o)


# ===================================================================== footer network
def network(th: str) -> str:
    c = THEMES[th]
    W, H = 1280, 300
    rng = random.Random(42)
    P = 6.0
    o = svg_open(W, H, "Thanks for reading. A small spiking network: spikes travel along synapses from layer to layer.")
    o.append(f"""<defs><radialGradient id="ng"><stop offset="0" stop-color="{c['hi']}" stop-opacity=".95"/><stop offset="1" stop-color="{c['hi']}" stop-opacity="0"/></radialGradient>
<pattern id="dots2" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="{c['dot']}"/></pattern></defs>""")
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="{c["bg"]}" stroke="{c["border"]}"/>')
    o.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="url(#dots2)"/>')
    o.append(f'<text x="64" y="118" font-family="{SANS}" font-size="40" font-weight="650" letter-spacing="-.8" fill="{c["fg"]}">Thanks for reading.</text>')
    o.append(f'<rect x="66" y="138" width="60" height="3" rx="1.5" fill="{c["acc"]}"/><rect x="130" y="138" width="9" height="3" rx="1.5" fill="{c["hi"]}"/>')
    o.append(f'<text x="64" y="182" font-family="{SANS}" font-size="19" fill="{c["muted"]}">Let’s build things that compute only</text>')
    o.append(f'<text x="64" y="208" font-family="{SANS}" font-size="19" fill="{c["muted"]}">when something happens.</text>')
    o.append(f'<text x="64" y="252" font-family="{MONO}" font-size="13" fill="{c["acc"]}">→ axel.cffrd.dnty@icloud.com</text>')
    layers = [5, 7, 7, 4, 2]
    xs = [640, 780, 920, 1060, 1190]
    nodes = []
    for li, n in enumerate(layers):
        col = []
        for k in range(n):
            yy = 150 + (k - (n - 1) / 2) * (232 / max(n, 2)) + rng.uniform(-6, 6)
            col.append((xs[li] + rng.uniform(-10, 10), yy))
        nodes.append(col)
    edges = {}
    for li in range(len(layers) - 1):
        for a, pa in enumerate(nodes[li]):
            for b, pb in enumerate(nodes[li + 1]):
                if rng.random() < 0.3 or (b == a % len(nodes[li + 1])):
                    mx = (pa[0] + pb[0]) / 2
                    d = f"M{pa[0]:.1f},{pa[1]:.1f} C{mx:.1f},{pa[1]:.1f} {mx:.1f},{pb[1]:.1f} {pb[0]:.1f},{pb[1]:.1f}"
                    edges[(li, a, b)] = d
                    o.append(f'<path d="{d}" fill="none" stroke="{c["border"]}" stroke-width="1.2"/>')
    # cascades: events (layer, node, time)
    travel = 0.55
    fires = []
    for w0 in (0.2, 2.2, 4.2):
        frontier = [(0, rng.randrange(layers[0]), w0)]
        fires.append(frontier[0])
        for li in range(len(layers) - 1):
            nxt = {}
            for (l, a, t0) in frontier:
                outs = [(b, d) for (ll, aa, b), d in edges.items() if ll == l and aa == a]
                rng.shuffle(outs)
                for b, d in outs[:2]:
                    o.append(f'<circle r="3.6" fill="{c["hi"]}" opacity="0"><animateMotion path="{d}" {smil_cycle(P, t0)} keyPoints="0;1;1" keyTimes="{kt(0, travel/P, 1)}" calcMode="linear"/>'
                             f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="{kt(0, .005, travel/P, travel/P + .005, 1)}" {smil_cycle(P, t0)}/></circle>')
                    nxt.setdefault(b, t0 + travel)
            frontier = [(li + 1, b, t) for b, t in nxt.items()]
            fires.extend(frontier)
            if not frontier:
                break
    for li, col in enumerate(nodes):
        for k, (x, y) in enumerate(col):
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{c["panel"]}" stroke="{c["acc"]}" stroke-width="1.8"/>')
    for (li, k, t0) in fires:
        x, y = nodes[li][k]
        t0 = t0 % P
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="17" fill="url(#ng)" opacity="0"><animate attributeName="opacity" values="0;1;0;0" keyTimes="{kt(0, .01, .09, 1)}" {smil_cycle(P, t0)}/></circle>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{c["hi"]}" opacity="0"><animate attributeName="opacity" values="0;1;0;0" keyTimes="{kt(0, .01, .07, 1)}" {smil_cycle(P, t0)}/></circle>')
    o.append('</svg>')
    return "\n".join(o)


# ===================================================================== typing taglines
TAGLINES = [
    "I find the bugs that don’t crash.",
    "Spiking neural networks · Brian2 · SpikingJelly · snnTorch",
    "On-device inference · PyTorch ExecuTorch · MLX · C++",
    "Computational neuroscience · HSSM · Neo · Neuropixels",
    "Open to full-time roles & contracts. Let’s talk.",
]


def typing(th: str) -> str:
    c = THEMES[th]
    W, H = 1280, 76
    fs, cw = 26, 15.65
    slot = 3.6
    P = slot * len(TAGLINES)
    o = svg_open(W, H, " / ".join(TAGLINES))
    st = [f".cv{{fill:{c['bg']}}}.cu{{fill:{c['hi']}}}"]
    body = []
    for i, line in enumerate(TAGLINES):
        n = len(line)
        tw = n * cw
        x0 = (W - tw) / 2
        a0 = i * slot / P * 100
        r1 = (i * slot + 1.3) / P * 100
        h1 = (i * slot + 2.8) / P * 100
        e1 = (i * slot + 3.3) / P * 100
        a1 = ((i + 1) * slot) / P * 100
        st.append(f".g{i}{{opacity:0;animation:v{i} {P}s linear infinite}}"
                  f"@keyframes v{i}{{0%,{max(a0-0.01,0):.2f}%{{opacity:0}}{a0:.2f}%,{a1-0.05:.2f}%{{opacity:1}}{a1:.2f}%,100%{{opacity:0}}}}")
        st.append(f".m{i}{{animation:t{i} {P}s infinite}}"
                  f"@keyframes t{i}{{0%,{a0:.2f}%{{transform:translateX(0);animation-timing-function:steps({n},end)}}"
                  f"{r1:.2f}%,{h1:.2f}%{{transform:translateX({tw:.1f}px);animation-timing-function:steps({n},end)}}"
                  f"{e1:.2f}%,100%{{transform:translateX(0)}}}}")
        col = c["fg"] if i else c["hi"]
        body.append(f'<g class="g{i}"><text x="{x0:.1f}" y="{H/2+9}" font-family="{MONO}" font-size="{fs}" fill="{col}" xml:space="preserve">{esc(line)}</text>'
                    f'<g class="m{i}"><rect class="cv" x="{x0:.1f}" y="10" width="{tw+40:.1f}" height="{H-20}"/>'
                    f'<rect class="cu" x="{x0+2:.1f}" y="{H/2-14}" width="3" height="30"/></g></g>')
    o.append("<style>" + "".join(st) + "</style>")
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="{c["bg"]}" stroke="{c["border"]}"/>')
    o.append(f'<text x="28" y="{H/2+5}" font-family="{MONO}" font-size="15" fill="{c["acc"]}">~/AxelNoun $</text>')
    o.extend(body)
    o.append("</svg>")
    return "\n".join(o)


# ===================================================================== activity raster (live data)
def activity(th: str, days: list[dict] | None, total: int | None, updated: str | None) -> str:
    """GitHub contribution calendar drawn as a spike raster: one row per weekday, one column per week."""
    c = THEMES[th]
    W, H = 1280, 300
    x0, y0, cs, rs = 112, 96, 21, 22
    P = 9.0
    o = svg_open(W, H, f"GitHub activity over the last 12 months as a spike raster: {total if total is not None else 'pending'} contributions.")
    o.append(f"""<defs><linearGradient id="atr" x1="0" x2="1"><stop offset="0" stop-color="{c['acc']}" stop-opacity="0"/><stop offset="1" stop-color="{c['acc']}" stop-opacity=".16"/></linearGradient></defs>
<style>.k{{opacity:.85;animation:fk {P}s linear infinite}}
@keyframes fk{{0%{{fill:{c['hi']};opacity:1}}6%{{opacity:1}}12%{{fill:var(--c)}}45%,100%{{fill:var(--c);opacity:.55}}}}
.cur{{animation:sw {P}s linear infinite}}@keyframes sw{{0%{{transform:translateX(0);opacity:0}}2%{{opacity:1}}97%{{opacity:1}}100%{{transform:translateX({53*cs}px);opacity:0}}}}</style>""")
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{c["panel"]}" stroke="{c["border"]}"/>')
    o.append(f'<text x="34" y="40" font-family="{MONO}" font-size="13" letter-spacing="2" fill="{c["acc"]}">ACTIVITY · LAST 12 MONTHS · LIVE</text>')
    sub = (f"{total:,} contributions, one spike per active day" if total is not None else "First refresh pending (updated daily by GitHub Actions)")
    o.append(f'<text x="34" y="68" font-family="{SANS}" font-size="21" font-weight="600" fill="{c["fg"]}">{esc(sub)}</text>')
    if updated:
        o.append(f'<text x="{W-34}" y="40" text-anchor="end" font-family="{MONO}" font-size="12" fill="{c["faint"]}">updated {esc(updated)}</text>')
    for r, lab in [(0, "Sun"), (1, "Mon"), (3, "Wed"), (5, "Fri")]:
        o.append(f'<text x="{x0-16}" y="{y0+r*rs+4}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{c["faint"]}">{lab}</text>')
    for r in range(7):
        o.append(f'<line x1="{x0}" x2="{x0+53*cs}" y1="{y0+r*rs}" y2="{y0+r*rs}" stroke="{c["border"]}" stroke-width=".6" opacity=".6"/>')
    if days:
        import datetime as _dt
        counts = sorted(d["count"] for d in days if d["count"] > 0) or [1]
        def q(v):
            k = sum(1 for x in counts if x <= v) / len(counts)
            return c["vir"][2] if k < .5 else (c["vir"][3] if k < .85 else c["hi"])
        first = _dt.date.fromisoformat(days[0]["date"])
        start = first - _dt.timedelta(days=(first.weekday() + 1) % 7)
        last_month = None
        for d in days:
            day = _dt.date.fromisoformat(d["date"])
            col = (day - start).days // 7
            row = (day.weekday() + 1) % 7
            x = x0 + col * cs + cs / 2
            if day.day <= 7 and day.month != last_month and row == 0:
                last_month = day.month
                o.append(f'<text x="{x-6:.1f}" y="{y0+6*rs+30}" font-family="{MONO}" font-size="11" fill="{c["faint"]}">{day.strftime("%b")}</text>')
            if d["count"] <= 0:
                continue
            h = min(18, 5 + 4 * math.log2(1 + d["count"]))
            delay = (x - x0) / (53 * cs) * P - P
            colr = q(d["count"])
            o.append(f'<rect class="k" style="--c:{colr};animation-delay:{delay:.2f}s" x="{x-1.4:.1f}" y="{y0+row*rs-h/2:.1f}" width="2.8" height="{h:.1f}" rx="1.3" fill="{colr}"/>')
    o.append(f'<g class="cur"><rect x="{x0-60}" y="{y0-16}" width="60" height="{6*rs+32}" fill="url(#atr)"/><line x1="{x0}" x2="{x0}" y1="{y0-18}" y2="{y0+6*rs+18}" stroke="{c["hi"]}" opacity=".7"/></g>')
    o.append(f'<text x="34" y="{H-20}" font-family="{MONO}" font-size="12" fill="{c["faint"]}">// silent days cost nothing: that is the point of event-driven hardware</text>')
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    for th in ("dark",):  # the profile is dark-only; "light" variants remain available in THEMES
        for name, fn in [("triptych", triptych), ("axon", axon), ("footer", network), ("typing", typing)]:
            with open(os.path.join(OUT, f"{name}-{th}.svg"), "w") as f:
                f.write(fn(th))
        act = os.path.join(OUT, f"activity-{th}.svg")
        if not os.path.exists(act):
            with open(act, "w") as f:
                f.write(activity(th, None, None, None))
    with open(os.path.join(OUT, "terminal.svg"), "w") as f:
        f.write(terminal())
    print("ok")
