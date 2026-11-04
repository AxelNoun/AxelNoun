"""Generate the SVG assets for the AxelNoun profile README.

Run:  python3 tools/make_assets.py   (writes into ../assets)
Every number shown in the images lives in this file: edit, re-run, commit.
"""
from __future__ import annotations

import math
import os
import random

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(OUT, exist_ok=True)

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

THEMES = {
    "dark": dict(bg="#0D1117", panel="#161B22", border="#30363D", fg="#E6EDF3", muted="#8B949E",
                 faint="#6E7681", dot="#1C2129", rest=".3", vrest=".38", acc="#35B779", acc2="#21918C", hi="#FDE725",
                 chip="#1F2630", chipfg="#C9D1D9", vir=["#440154", "#3B528B", "#21918C", "#5EC962", "#FDE725"]),
    "light": dict(bg="#FFFFFF", panel="#F6F8FA", border="#D0D7DE", fg="#1F2328", muted="#59636E",
                  faint="#818B98", dot="#EAEEF2", rest=".46", vrest=".55", acc="#1F8A70", acc2="#2C728E", hi="#E36209",
                  chip="#EFF2F5", chipfg="#424A53", vir=["#440154", "#3B528B", "#21918C", "#5EC962", "#C9B800"]),
}

T = 7.0  # sweep period, seconds


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- spike data
def lif_trace(x0: float, w: float, bursts: list[float], rng: random.Random):
    """Leaky integrate-and-fire neuron driven by noise + the population bursts.
    Returns (points in normalised V, spike x positions)."""
    n = int(w)
    v, pts, spikes = 0.0, [], []
    tau, refr = 22.0, 0
    for i in range(n):
        x = x0 + i
        drive = 0.030 + 0.020 * math.sin(i / 37.0)
        for b in bursts:
            drive += 0.11 * math.exp(-((x - b) ** 2) / (2 * 6.0 ** 2))
        drive += rng.gauss(0, 0.012)
        if refr > 0:
            refr -= 1
            v = 0.0
        else:
            v += -v / tau + drive
        if v >= 1.0:
            pts.append((x, 1.0))
            pts.append((x, 1.65))  # spike apex
            spikes.append(x)
            v, refr = 0.0, 4
            pts.append((x + 0.6, 0.0))
        else:
            pts.append((x, max(v, -0.05)))
    return pts, spikes


def raster(x0, w, rows, bursts, special_row, special_spikes, rng):
    data = []
    for r in range(rows):
        if r == special_row:
            data.append(list(special_spikes))
            continue
        rate = rng.uniform(6, 13)  # spikes per sweep
        xs, x = [], x0
        while True:
            x += rng.expovariate(rate / w)
            if x > x0 + w - 2:
                break
            xs.append(x)
        for b in bursts:
            if rng.random() < 0.86:
                xs.append(b + rng.gauss(0, 2.4))
        data.append(sorted(xx for xx in xs if x0 + 1 < xx < x0 + w - 2))
    return data


def delay(x, x0, w):
    t = (x - x0) / w * T
    return f"{t - T:.3f}s"


# ---------------------------------------------------------------- banner
def banner(th: str) -> str:
    c = THEMES[th]
    rng = random.Random(7)
    W, H = 1280, 360
    x0, rw = 752, 464
    bursts = [x0 + 96, x0 + 251, x0 + 377]
    rows, ry0, rstep = 12, 74, 12.5
    special = 9
    pts, sp = lif_trace(x0, rw, bursts, random.Random(11))
    data = raster(x0, rw, rows, bursts, special, sp, rng)

    # V(t) geometry
    vy_rest, vy_th = 312, 266
    def vy(v):
        return vy_rest - v * (vy_rest - vy_th)

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
             f'aria-label="Axel Coiffard-Donaty. Machine learning engineer: spiking neural networks, computational neuroscience, efficient inference.">')
    o.append(f"""<defs>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="{c['dot']}"/></pattern>
<linearGradient id="trail" x1="0" x2="1"><stop offset="0" stop-color="{c['acc']}" stop-opacity="0"/><stop offset="1" stop-color="{c['acc']}" stop-opacity=".16"/></linearGradient>
<linearGradient id="fadeR" x1="0" x2="1"><stop offset=".55" stop-color="{c['bg']}" stop-opacity="0"/><stop offset="1" stop-color="{c['bg']}" stop-opacity=".9"/></linearGradient>
</defs>
<style>
.s{{fill:{c['acc']};opacity:.8;animation:fs {T}s linear infinite}}
.s.k{{fill:{c['acc2']}}}
@keyframes fs{{0%{{fill:{c['hi']};opacity:1}}9%{{opacity:1}}14%{{fill:{c['acc']}}}48%{{opacity:{c['rest']}}}100%{{fill:{c['acc']};opacity:{c['rest']}}}}}
.vb{{fill:none;stroke:{c['acc']};stroke-width:1.6;stroke-linejoin:round;opacity:{c['vrest']}}}
.vf{{fill:none;stroke:{c['hi']};stroke-width:2;stroke-linecap:round;opacity:0;animation:fv {T}s linear infinite}}
@keyframes fv{{0%{{opacity:1}}22%{{opacity:0}}100%{{opacity:0}}}}
.cur{{animation:sw {T}s linear infinite}}
@keyframes sw{{0%{{transform:translateX(0);opacity:0}}3%{{opacity:1}}96%{{opacity:1}}100%{{transform:translateX({rw}px);opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.s,.vf,.cur{{animation:none}}.cur{{display:none}}.vb{{opacity:.85}}}}
</style>""")
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="{c["bg"]}" stroke="{c["border"]}"/>')
    o.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="url(#dots)" opacity=".9"/>')

    # ---- left: identity
    o.append(f'<g font-family="{SANS}">')
    o.append(f'<text x="64" y="96" font-family="{MONO}" font-size="13" letter-spacing="2.2" fill="{c["acc"]}">NEUROMORPHIC · NEUROSCIENCE · INFERENCE</text>')
    o.append(f'<text x="62" y="160" font-size="56" font-weight="650" letter-spacing="-1" fill="{c["fg"]}">Axel Coiffard-Donaty</text>')
    o.append(f'<rect x="64" y="184" width="72" height="3" rx="1.5" fill="{c["acc"]}"/>')
    o.append(f'<rect x="140" y="184" width="10" height="3" rx="1.5" fill="{c["hi"]}"/>')
    o.append(f'<text x="64" y="232" font-size="21" fill="{c["muted"]}">Machine learning engineer. I make sure spiking</text>')
    o.append(f'<text x="64" y="261" font-size="21" fill="{c["muted"]}">networks, neuroscience tools and inference</text>')
    o.append(f'<text x="64" y="290" font-size="21" fill="{c["muted"]}">runtimes compute what they claim to.</text>')
    o.append('</g>')

    # ---- right: raster
    o.append(f'<g font-family="{MONO}" font-size="11" fill="{c["faint"]}">')
    o.append(f'<text x="{x0-14}" y="{ry0+4}" text-anchor="end">n₁</text>')
    o.append(f'<text x="{x0-14}" y="{ry0+special*rstep+4}" text-anchor="end" fill="{c["acc2"]}">n₁₀</text>')
    o.append(f'<text x="{x0-14}" y="{ry0+(rows-1)*rstep+4}" text-anchor="end">n₁₂</text>')
    o.append(f'<text x="{x0-14}" y="{vy_th+4}" text-anchor="end">θ</text>')
    o.append(f'<text x="{x0-14}" y="{vy_rest-2}" text-anchor="end">V₁₀</text>')
    o.append(f'<text x="{x0+rw}" y="{H-22}" text-anchor="end">t →   // compute only when something happens</text>')
    o.append('</g>')
    # threshold line
    o.append(f'<line x1="{x0}" x2="{x0+rw}" y1="{vy_th}" y2="{vy_th}" stroke="{c["faint"]}" stroke-dasharray="3 5" opacity=".7"/>')
    # link row 10 to its trace
    o.append(f'<rect x="{x0-4}" y="{ry0+special*rstep-6.5}" width="{rw+8}" height="11" rx="3" fill="{c["acc2"]}" opacity=".10"/>')
    for r, xs in enumerate(data):
        y = ry0 + r * rstep - 4
        k = " k" if r == special else ""
        for x in xs:
            o.append(f'<rect class="s{k}" x="{x:.1f}" y="{y:.1f}" width="2.2" height="8" rx="1" style="animation-delay:{delay(x, x0, rw)}"/>')
    # V(t): base path
    d = "M" + " L".join(f"{x:.1f},{vy(v):.1f}" for x, v in pts)
    o.append(f'<path class="vb" d="{d}"/>')
    # V(t): phosphor overlay, chunked by x
    chunk, cur = [], []
    start = pts[0][0]
    for p in pts:
        cur.append(p)
        if p[0] - start >= 6:
            chunk.append(cur)
            cur = [p]
            start = p[0]
    if len(cur) > 1:
        chunk.append(cur)
    for seg in chunk:
        dd = "M" + " L".join(f"{x:.1f},{vy(v):.1f}" for x, v in seg)
        o.append(f'<path class="vf" d="{dd}" style="animation-delay:{delay(seg[0][0], x0, rw)}"/>')
    # sweep cursor
    o.append(f'<g class="cur"><rect x="{x0-70}" y="{ry0-12}" width="70" height="{vy_rest-ry0+20}" fill="url(#trail)"/>'
             f'<line x1="{x0}" x2="{x0}" y1="{ry0-14}" y2="{vy_rest+8}" stroke="{c["hi"]}" stroke-width="1.4" opacity=".75"/></g>')
    o.append('</svg>')
    return "\n".join(o)


# ---------------------------------------------------------------- stats strip
STATS = [
    ("25+", "", "pull requests merged upstream", "each reviewed by the project’s maintainers"),
    ("9", "", "open-source projects", "ExecuTorch · Brian2 · SpikingJelly · HSSM · …"),
    ("73→80", " tok/s", "Qwen3.5 decode, ExecuTorch MLX", "MoE expert-sort #20685, measured by reviewer"),
]


def stats(th: str) -> str:
    c = THEMES[th]
    W, H = 1280, 168
    cw = W / len(STATS)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="25+ pull requests merged upstream; 9 open-source projects; Qwen3.5 decode from 73 to 80 tokens per second in ExecuTorch">']
    o.append(f"""<style>.tk{{fill:{c['acc']};opacity:.25;animation:tk 4.2s linear infinite}}
@keyframes tk{{0%{{fill:{c['hi']};opacity:1}}8%{{fill:{c['acc']};opacity:1}}70%{{opacity:.9}}90%,100%{{opacity:.25}}}}
.rn{{fill:{c['acc']};opacity:.5;animation:rn 2.25s ease-in-out infinite}}@keyframes rn{{0%{{fill:{c['hi']};opacity:1}}25%{{fill:{c['acc']};opacity:.5}}100%{{opacity:.5}}}}
.gr{{transform-box:fill-box;transform-origin:left center;animation:gr 3.2s ease-in-out infinite}}
@keyframes gr{{0%,15%{{transform:scaleX(.9125)}}55%,100%{{transform:scaleX(1)}}}}</style>""")
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{c["panel"]}" stroke="{c["border"]}"/>')
    for i, (big, unit, label, note) in enumerate(STATS):
        x = i * cw + 48
        if i:
            o.append(f'<line x1="{i*cw:.0f}" x2="{i*cw:.0f}" y1="30" y2="{H-30}" stroke="{c["border"]}"/>')
        o.append(f'<text x="{x:.0f}" y="78" font-family="{SANS}" font-size="50" font-weight="650" letter-spacing="-1" fill="{c["fg"]}">'
                 f'{esc(big)}<tspan font-size="22" font-weight="500" fill="{c["acc"]}" letter-spacing="0">{esc(unit)}</tspan></text>')
        if i == 0:  # one spike per merged PR, lighting up in turn
            o.append(f'<rect x="{x:.0f}" y="94" width="28" height="3" rx="1.5" fill="{c["acc"]}"/>')
            for k in range(25):
                gx, gy = i * cw + 300 + (k % 13) * 7.5, 40 + (k // 13) * 26
                o.append(f'<rect class="tk" style="animation-delay:{k*0.14:.2f}s" x="{gx:.1f}" y="{gy}" width="2.6" height="18" rx="1.2"/>')
        elif i == 1:  # nine projects as a ring of nodes
            o.append(f'<rect x="{x:.0f}" y="94" width="28" height="3" rx="1.5" fill="{c["acc"]}"/>')
            ccx, ccy, rr = i * cw + 340, 62, 26
            for k in range(9):
                a1 = -math.pi / 2 + k * 2 * math.pi / 9
                px, py = ccx + rr * math.cos(a1), ccy + rr * math.sin(a1)
                o.append(f'<line x1="{ccx}" y1="{ccy}" x2="{px:.1f}" y2="{py:.1f}" stroke="{c["border"]}" stroke-width="1.2"/>')
                o.append(f'<circle class="rn" style="animation-delay:{k*0.25-2.25:.2f}s" cx="{px:.1f}" cy="{py:.1f}" r="5"/>')
            o.append(f'<circle cx="{ccx}" cy="{ccy}" r="6" fill="{c["acc2"]}"/>')
        else:  # decode speed: the 80 bar grows past the 73 one
            o.append(f'<rect x="{x:.0f}" y="91" width="{73*1.7:.0f}" height="4" rx="2" fill="{c["faint"]}" opacity=".45"/>')
            o.append(f'<rect class="gr" x="{x:.0f}" y="98" width="{80*1.7:.0f}" height="4" rx="2" fill="{c["hi"]}"/>')
        o.append(f'<text x="{x:.0f}" y="122" font-family="{SANS}" font-size="17" fill="{c["fg"]}" opacity=".88">{esc(label)}</text>')
        o.append(f'<text x="{x:.0f}" y="144" font-family="{MONO}" font-size="12" fill="{c["faint"]}">{esc(note)}</text>')
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- project cards
CARDS = [
    dict(slug="neurovis3d", title="NeuroVis3D", tag="SPIKING NETWORKS · DIAGNOSTICS",
         desc=["Live diagnostics for SNNs trained with surrogate",
               "gradients: dead neurons, sparsity collapse and", "temporal gradient decay, via PyTorch hooks."],
         chips=["Python", "snnTorch", "work in progress"], glyph="heat"),
    dict(slug="tpl-lab", title="TPL-Lab", tag="NEUROPIXELS · FALSIFICATION",
         desc=["A speculative theory of perception turned into a",
               "pre-registered test on Allen Neuropixels data.", "Result: refuted in 12 of 12 area × session pairs."],
         chips=["Python", "pre-registered", "negative result"], glyph="cloud"),
    dict(slug="kinoscope", title="KinoScope", tag="PROTEIN AI · DRUG DISCOVERY",
         desc=["Kinase–inhibitor affinity with a GNN × ESM-2",
               "model, under a leakage-free evaluation protocol", "(random, cold-drug, cold-target, temporal)."],
         chips=["PyTorch", "RDKit", "mypy --strict"], glyph="mol"),
    dict(slug="discoursekit", title="discoursekit", tag="LANGUAGE · RESEARCH TOOLING",
         desc=["Linguistic measures for discourse research,",
               "each tied to a published definition and", "tested against it. Not a clinical tool."],
         chips=["Python", "UAX #29", "alpha"], glyph="text"),
]


def glyph(kind: str, c: dict, gx: float, gy: float) -> str:
    """Animated glyph drawn at the top-right of a project card."""
    o = []
    rng = random.Random(kind)
    if kind == "heat":  # NeuroVis3D: gradient magnitude per layer x timestep, flowing back in time
        o.append("<style>.hc{animation:hp 2.8s ease-in-out infinite}@keyframes hp{0%,100%{opacity:.35}45%{opacity:1}}</style>")
        cols, rows_, s = 7, 4, 15
        for r in range(rows_):
            for k in range(cols):
                v = max(0.0, 1 - (k / cols) * (0.6 + 0.35 * r) + rng.uniform(-.12, .12))
                idx = min(4, max(0, int(v * 4.99)))
                d = -((cols - 1 - k) * 0.22 + r * 0.08)
                o.append(f'<rect class="hc" style="animation-delay:{d:.2f}s" x="{gx+k*(s+3)}" y="{gy+r*(s+3)}" width="{s}" height="{s}" rx="2.5" fill="{c["vir"][idx]}"/>')
    elif kind == "cloud":  # TPL-Lab: a point cloud that is not a sphere
        o.append("<style>.pt{animation:d0 3.6s ease-in-out infinite alternate}.p1{animation-name:d1}.p2{animation-name:d2}.p3{animation-name:d3}"
                 "@keyframes d0{to{transform:translate(3px,-2px)}}@keyframes d1{to{transform:translate(-3px,2px)}}"
                 "@keyframes d2{to{transform:translate(2px,3px)}}@keyframes d3{to{transform:translate(-2px,-3px)}}"
                 ".xx{animation:xp 2.2s ease-in-out infinite}@keyframes xp{0%,100%{opacity:.35}50%{opacity:1}}"
                 ".rg{animation:rg 6s linear infinite;stroke-dasharray:3 4}@keyframes rg{to{stroke-dashoffset:-70}}</style>")
        cx, cy, R = gx + 62, gy + 36, 36
        o.append(f'<circle class="rg" cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{c["faint"]}"/>')
        for i in range(46):
            a = rng.uniform(0, 2 * math.pi)
            rr = abs(rng.gauss(0, 0.55)) * R * 1.15
            o.append(f'<circle class="pt p{i % 4}" style="animation-delay:{-rng.uniform(0, 3.6):.2f}s" cx="{cx+rr*math.cos(a):.1f}" cy="{cy+rr*math.sin(a)*0.8:.1f}" r="1.9" fill="{c["acc"]}" opacity=".8"/>')
        o.append(f'<path class="xx" d="M{cx+R-6},{cy-R-4} l14,14 m0,-14 l-14,14" stroke="{c["hi"]}" stroke-width="2.4" stroke-linecap="round"/>')
    elif kind == "mol":  # KinoScope: a ligand graph, message passing atom to atom
        o.append("<style>.at{animation:at 2.4s ease-in-out infinite}@keyframes at{0%,100%{opacity:.45}20%{opacity:1}40%{opacity:.45}}"
                 ".bd{stroke-dasharray:4 4;animation:bd 1.6s linear infinite}@keyframes bd{to{stroke-dashoffset:-16}}</style>")
        cx, cy, R = gx + 50, gy + 36, 22
        pts = [(cx + R * math.cos(math.pi / 6 + i * math.pi / 3), cy + R * math.sin(math.pi / 6 + i * math.pi / 3)) for i in range(6)]
        extra = [(pts[0][0] + 24, pts[0][1] + 8), (pts[3][0] - 24, pts[3][1] - 8), (pts[4][0] + 6, pts[4][1] - 22), (pts[0][0] + 44, pts[0][1] - 6)]
        edges = [(pts[i], pts[(i + 1) % 6]) for i in range(6)] + [(pts[0], extra[0]), (pts[3], extra[1]), (pts[4], extra[2]), (extra[0], extra[3])]
        for a, b in edges:
            o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{c["faint"]}" stroke-width="2"/>')
        for a, b in edges:
            o.append(f'<line class="bd" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{c["acc"]}" stroke-width="1.2" opacity=".7"/>')
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{R*0.55:.1f}" fill="none" stroke="{c["faint"]}" stroke-width="1.4" opacity=".7"/>')
        for i, p in enumerate(pts + extra):
            col = c["hi"] if i in (7, 9) else (c["acc2"] if i in (2, 6) else c["acc"])
            o.append(f'<circle class="at" style="animation-delay:{-(2.4 - i * 0.24):.2f}s" cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="4.6" fill="{col}"/>')
    elif kind == "text":  # discoursekit: coherence arcs between successive units, one topic break
        o.append("<style>.arc{stroke-dasharray:40;animation:dw 4.8s ease-out infinite}"
                 "@keyframes dw{0%{stroke-dashoffset:40}25%,80%{stroke-dashoffset:0}100%{stroke-dashoffset:-40}}"
                 ".brk{animation:bk 1.2s steps(1) infinite}@keyframes bk{50%{opacity:.2}}"
                 ".ln{animation:ln 4.8s ease-in-out infinite}@keyframes ln{0%,100%{opacity:.4}20%{opacity:.85}}</style>")
        ys = [gy + 6 + i * 13 for i in range(6)]
        lens = [96, 80, 104, 62, 92, 74]
        for i, (y, L) in enumerate(zip(ys, lens)):
            o.append(f'<rect class="ln" style="animation-delay:{i*0.35-4.8:.2f}s" x="{gx+24}" y="{y}" width="{L}" height="5" rx="2.5" fill="{c["faint"]}"/>')
        for j, (a, b) in enumerate([(0, 1), (1, 2), (2, 4), (4, 5)]):
            ya, yb = ys[a] + 2.5, ys[b] + 2.5
            o.append(f'<path class="arc" style="animation-delay:{j*0.45-4.8:.2f}s" d="M{gx+20},{ya} C{gx+4},{ya} {gx+4},{yb} {gx+20},{yb}" fill="none" stroke="{c["acc"]}" stroke-width="1.8"/>')
        o.append(f'<path class="brk" d="M{gx+20},{ys[2]+2.5} C{gx-6},{ys[2]} {gx-6},{ys[3]+5} {gx+20},{ys[3]+2.5}" fill="none" stroke="{c["hi"]}" stroke-width="1.8" stroke-dasharray="3 3"/>')
    return "\n".join(o)


def card(cd: dict, th: str) -> str:
    c = THEMES[th]
    W, H = 640, 220
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(cd["title"])}: {esc(" ".join(cd["desc"]))}">']
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" fill="{c["panel"]}" stroke="{c["border"]}"/>')
    o.append(f'<text x="30" y="42" font-family="{MONO}" font-size="12" letter-spacing="1.6" fill="{c["acc"]}">{esc(cd["tag"])}</text>')
    o.append(f'<text x="29" y="82" font-family="{SANS}" font-size="30" font-weight="650" letter-spacing="-.5" fill="{c["fg"]}">{esc(cd["title"])}</text>')
    for i, line in enumerate(cd["desc"]):
        o.append(f'<text x="30" y="{112+i*21}" font-family="{SANS}" font-size="15.5" fill="{c["muted"]}">{esc(line)}</text>')
    x = 30
    for ch in cd["chips"]:
        w = 16 + len(ch) * 7.3
        o.append(f'<rect x="{x}" y="{H-46}" width="{w:.0f}" height="24" rx="12" fill="{c["chip"]}" stroke="{c["border"]}"/>')
        o.append(f'<text x="{x+w/2:.0f}" y="{H-29.5}" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{c["chipfg"]}">{esc(ch)}</text>')
        x += w + 8
    o.append(glyph(cd["glyph"], c, 478, 30))
    o.append(f'<text x="{W-28}" y="{H-29.5}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{c["faint"]}">AxelNoun/{esc(cd["slug"])} ↗</text>')
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- divider
def divider(th: str) -> str:
    c = THEMES[th]
    W, H = 1280, 40
    rng = random.Random(3)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="">']
    o.append(f"""<style>.s{{fill:{c['acc']};opacity:.5;animation:fs {T*1.6}s linear infinite}}
@keyframes fs{{0%{{fill:{c['hi']};opacity:1}}10%{{opacity:1}}16%{{fill:{c['acc']}}}50%{{opacity:.28}}100%{{fill:{c['acc']};opacity:.28}}}}
@media (prefers-reduced-motion: reduce){{.s{{animation:none}}}}</style>""")
    o.append(f'<line x1="0" x2="{W}" y1="{H/2}" y2="{H/2}" stroke="{c["border"]}"/>')
    x = 8.0
    while x < W - 8:
        x += rng.expovariate(1 / 26)
        if x >= W - 8:
            break
        h = rng.choice([10, 14, 18, 22])
        t = x / W * T * 1.6
        o.append(f'<rect class="s" x="{x:.1f}" y="{H/2-h/2:.1f}" width="2.2" height="{h}" rx="1" style="animation-delay:{t - T*1.6:.3f}s"/>')
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    for th in ("dark",):  # dark-only profile
        with open(os.path.join(OUT, f"banner-{th}.svg"), "w") as f:
            f.write(banner(th))
        with open(os.path.join(OUT, f"stats-{th}.svg"), "w") as f:
            f.write(stats(th))
        for cd in CARDS:
            with open(os.path.join(OUT, f"card-{cd['slug']}-{th}.svg"), "w") as f:
                f.write(card(cd, th))
    print("ok", sorted(os.listdir(OUT)))
