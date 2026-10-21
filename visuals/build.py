"""Génère les visuels et les blocs de texte publics à partir des données, et synchronise le portfolio et le README.

Consomme :
  visuals/data/github.json             instantané GitHub (fetch_github.py) : état et date de fusion de chaque PR,
                                       PR ouvertes, dépôts publics de l'auteur — les faits
  visuals/data/merged.json             PR fusionnées curées : résumés EN/FR, texte et citation du README, classes
                                       du Registre, notes des PR ouvertes, exclusions — le texte rédigé à la main
  visuals/data/projects.json           projets personnels curés : texte du README et du portfolio (EN/FR)
  silent-failures/registry/entries.js  les vingt classes du Registre (source unique de la page du Registre)
  visuals/templates/*.html, tokens.css gabarits de rendu et jetons du design system AxelNoun

Produit (seul le contenu entre marqueurs <!--nom:start--> … <!--nom:end--> est réécrit, rien d'autre) :
  github/README.md                     blocs merged (frise + tableau), open (PR en revue), projects
  portfolio/index.html                 blocs data, merged-count, project-count, range-*, open-*, projects-*
  github/assets/merged-{light,dark}.png             frise des fusions pour le README de profil
  (les images du Registre sont produites par silent-failures/registry/images.py, dans son propre dépôt)
  visuals/data/renders.json            empreinte des entrées de chaque image, pour ne re-rendre que ce qui a changé
  --report FICHIER                     (facultatif) liste « à relire » en Markdown, non versionnée

Hypothèses :
  - Les faits viennent de GitHub, le texte vient de vous. Une PR fusionnée que merged.json ne connaît pas encore
    est affichée avec son titre GitHub tel quel (aucun résumé n'est inventé) et signalée dans le rapport.
  - Si la date de merged.json diffère de celle de GitHub, la date de merged.json est conservée et l'écart est
    signalé : la corriger est une décision éditoriale. Si merged.json annonce fusionnée une PR que GitHub ne
    donne pas fusionnée, la construction échoue.
  - La fenêtre de la frise va du premier jour du mois de la première fusion au premier jour du mois qui suit la
    dernière : elle dépend des données seules, pas de la date d'exécution.
  - Node.js est installé : entries.js est un littéral JavaScript, il est évalué par Node plutôt que
    ré-analysé à la main en Python (une seule lecture de la source, pas de seconde grammaire à maintenir).
  - Google Chrome (ou Chromium) est installé ; chemin via la variable CHROME si la détection échoue.
  - Le rendu charge les polices depuis Google Fonts : hors ligne, Chrome retombe sur les polices de secours
    et les images restent lisibles mais ne respectent plus la typographie du design system.
  - Les PNG ne sont pas reproductibles à l'octet près (rendu des polices) ; les données, si. D'où renders.json :
    une image n'est re-rendue que si son HTML d'entrée a changé, sinon chaque exécution produirait un commit.
  - Disposition des dossiers : celle de ce dossier de livrables par défaut ; en CI, les variables PROFILE_DIR,
    PORTFOLIO et ENTRIES_JS (chemins relatifs à la racine) l'adaptent à la disposition du dépôt.

Usage :
  python visuals/build.py                  # synchronise README et portfolio, régénère les images modifiées
  python visuals/build.py --check          # échoue si un bloc généré n'est pas à jour
  python visuals/build.py --images merged  # seulement la frise du README (le Registre a sa propre CI)
  python visuals/build.py --images none --report a-relire.md --changes changes.json
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import hashlib
import html as htmlmod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISUALS = ROOT / "visuals"
DATA = VISUALS / "data"
MERGED_JSON = DATA / "merged.json"
PROJECTS_JSON = DATA / "projects.json"
SNAPSHOT = DATA / "github.json"
RENDER_HASHES = DATA / "renders.json"
TEMPLATES = VISUALS / "templates"
PROFILE = ROOT / os.environ.get("PROFILE_DIR", "github")
README = PROFILE / "README.md"
ENTRIES_JS = ROOT / os.environ.get("ENTRIES_JS", "silent-failures/registry/entries.js")
PORTFOLIO = ROOT / os.environ.get("PORTFOLIO", "portfolio/index.html")

# Taille de la fenêtre de rendu en pixels CSS ; facteur d'échelle 2 pour les README (écrans haute densité).
README_SCALE = 2
# Frise : en-tête, axe et marges (78 px) plus une ligne de 26 px par projet (cf. .lane dans merged.html).
MERGED_BASE_HEIGHT, MERGED_LANE_HEIGHT = 78, 26
RENDERS = [
    # groupe, gabarit, thème, sortie, largeur, hauteur (None : calculée), échelle
    ("merged", "merged.html", "light", PROFILE / "assets" / "merged-light.png", 880, None, README_SCALE),
    ("merged", "merged.html", "dark", PROFILE / "assets" / "merged-dark.png", 880, None, README_SCALE),
    # Les images du Registre (en-tête du README, prévisualisation sociale) sont rendues par le dépôt du Registre
    # lui-même : python silent-failures/registry/images.py, vérifié par sa CI.
]
CHROME_TIME_BUDGET_MS = 10000  # laisse le temps aux polices web de se charger avant la capture
# Colonne des noms de la frise (190 px en police mono 13 px) : au-delà de 23 caractères (« catalystneuro/neuroconv »,
# la plus longue étiquette curée), le nom déborde ; un projet ajouté automatiquement prend alors son nom court.
LANE_LABEL_MAX = 23

MONTHS = {"en": list(calendar.month_name)[1:],
          "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
                 "septembre", "octobre", "novembre", "décembre"]}
ARCHIVED = {"readme": "Archived.", "en": "archived", "fr": "archivé"}


def load_registry() -> list[dict]:
    """Évalue entries.js avec Node et renvoie, pour chaque classe, l'identifiant, la famille, la détectabilité et les noms."""
    node = shutil.which("node")
    if node is None:
        sys.exit("Node.js introuvable : il est nécessaire pour lire registry/entries.js.")
    script = (
        "const src=require('fs').readFileSync(0,'utf8');"
        "const {ENTRIES}=new Function(src+';return {ENTRIES};')();"
        "process.stdout.write(JSON.stringify(ENTRIES.map(e=>({id:e.id,family:e.family,detect:e.detect,en:e.en.name,fr:e.fr.name}))));"
    )
    out = subprocess.run([node, "-e", script], input=ENTRIES_JS.read_text(encoding="utf-8"),
                         capture_output=True, text=True, encoding="utf-8", check=True)
    reg = json.loads(out.stdout)
    if not reg:
        sys.exit("entries.js ne contient aucune entrée.")
    return reg


def repo_of(url: str) -> str:
    """'https://github.com/owner/name/pull/12' -> 'owner/name'."""
    parts = url.split("/")
    return f"{parts[3]}/{parts[4]}"


def load_snapshot() -> dict:
    if not SNAPSHOT.exists():
        sys.exit(f"{SNAPSHOT.relative_to(ROOT)} absent : lancer d'abord python visuals/fetch_github.py")
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def load_curated(registry_ids: set[str]) -> dict:
    """Charge merged.json et refuse les incohérences plutôt que de les corriger en silence."""
    data = json.loads(MERGED_JSON.read_text(encoding="utf-8"))
    lanes = {l["key"] for l in data["lanes"]}
    seen = set()
    errors = []
    for m in data["merged"]:
        try:
            dt.date.fromisoformat(m["date"])
        except ValueError:
            errors.append(f"date invalide : {m['date']!r} ({m['ref']})")
        if m["lane"] not in lanes:
            errors.append(f"projet inconnu {m['lane']!r} ({m['ref']})")
        if m["url"] in seen:
            errors.append(f"doublon : {m['url']}")
        seen.add(m["url"])
        for sf in m.get("sf", []):
            if sf not in registry_ids:
                errors.append(f"classe inconnue {sf} ({m['ref']})")
    if errors:
        sys.exit("merged.json incohérent :\n  " + "\n  ".join(errors))
    return data


def assemble(curated: dict, snapshot: dict, report: dict) -> tuple[dict, list[dict]]:
    """Combine le texte curé et les faits GitHub ; renvoie les données de la frise et les PR ouvertes à afficher."""
    pulls = {p["url"]: p for p in snapshot["pulls"]}
    excluded = set(curated.get("exclude", []))
    lanes = [dict(l) for l in curated["lanes"]]
    lane_of_repo = {repo_of(m["url"]): m["lane"] for m in curated["merged"]}
    errors = []
    merged = []
    for m in curated["merged"]:
        if m["url"] in excluded:
            continue
        p = pulls.get(m["url"])
        if p is None:
            errors.append(f"{m['ref']} absente de l'instantané GitHub (relancer fetch_github.py)")
            continue
        if p["state"] != "MERGED":
            errors.append(f"{m['ref']} : merged.json la donne fusionnée, GitHub dit {p['state']}")
            continue
        if p["merged"] != m["date"]:
            report["dates"].append({"ref": m["ref"], "url": m["url"], "curated": m["date"], "github": p["merged"]})
        merged.append(dict(m))
    if errors:
        sys.exit("merged.json contredit GitHub :\n  " + "\n  ".join(errors))

    known = {m["url"] for m in curated["merged"]}
    for p in snapshot["pulls"]:
        if p["state"] != "MERGED" or not p["by_author"] or p["url"] in known or p["url"] in excluded:
            continue
        repo = p["repo"]
        if repo not in lane_of_repo:
            key = repo.split("/")[1].lower()
            if key in {l["key"] for l in lanes}:
                key = repo.lower()
            lanes.append({"key": key, "label": repo if len(repo) <= LANE_LABEL_MAX else repo.split("/")[1]})
            lane_of_repo[repo] = key
        ref = f"{repo} #{p['number']}"
        # Aucun résumé n'est rédigé à votre place : le titre GitHub est affiché tel quel jusqu'à curation.
        merged.append({"date": p["merged"], "lane": lane_of_repo[repo], "ref": ref, "url": p["url"], "sf": [],
                       "en": p["title"], "fr": p["title"], "auto": True,
                       "readme": {"label": ref, "text": p["title"], "quote": "merged"}})
        report["pending"].append({"ref": ref, "url": p["url"], "date": p["merged"], "title": p["title"],
                                  "lane": lane_of_repo[repo]})
    # Tri stable : à date égale, l'ordre de merged.json est conservé, puis les PR non curées.
    merged.sort(key=lambda m: m["date"], reverse=True)

    dates = [dt.date.fromisoformat(m["date"]) for m in merged]
    if not dates:
        sys.exit("aucune PR fusionnée à afficher.")
    first, last = min(dates), max(dates)
    end = dt.date(last.year + (last.month == 12), last.month % 12 + 1, 1)
    window = {"start": first.strftime("%Y-%m"), "end": end.strftime("%Y-%m"),
              "en": range_label(first, last, "en", " → "), "fr": range_label(first, last, "fr", " → ")}

    open_pulls = [p for p in snapshot["pulls"]
                  if p["state"] == "OPEN" and not p["draft"] and p["by_author"] and p["url"] not in excluded]
    used_lanes = {m["lane"] for m in merged}
    lanes = [l for l in lanes if l["key"] in used_lanes]
    return {"lanes": lanes, "merged": merged, "window": window}, open_pulls


def range_label(first: dt.date, last: dt.date, lang: str, sep: str) -> str:
    a, b = MONTHS[lang][first.month - 1], MONTHS[lang][last.month - 1]
    if first.year != last.year:
        return f"{a} {first.year}{sep}{b} {last.year}"
    if first.month == last.month:
        return f"{a} {first.year}"
    return f"{a}{sep}{b} {first.year}"


def short_label(repo: str, lanes: list[dict], lane_of_repo: dict) -> str:
    """Nom court d'un projet : dernier segment de l'étiquette de sa ligne de frise, sinon owner/name."""
    key = lane_of_repo.get(repo)
    for l in lanes:
        if l["key"] == key:
            return l["label"].split("/")[-1]
    return repo


def script_json(obj) -> str:
    # JSON placé dans un <script> : "</" doit être échappé pour ne pas fermer la balise.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def page_data(data: dict) -> dict:
    """Données passées au portfolio et aux gabarits : sans le texte du README, qu'ils n'utilisent pas."""
    return {**data, "merged": [{k: v for k, v in m.items() if k != "readme"} for m in data["merged"]]}


def md_cell(s: str) -> str:
    return s.replace("|", "\\|")


def readme_blocks(data: dict, open_pulls: list[dict], curated: dict, projects: list[dict]) -> dict[str, str]:
    lane_rank = {l["key"]: i for i, l in enumerate(data["lanes"])}
    rows = sorted(data["merged"], key=lambda m: (lane_rank[m["lane"]], m["date"], m["url"]))
    win_en = data["window"]["en"].replace(" → ", " to ")
    table = "\n".join(
        f"| [{md_cell(m['readme']['label'])}]({m['url']}) | {md_cell(m['readme']['text'])} | {md_cell(m['readme']['quote'])} |"
        for m in rows)
    merged_block = (
        "\n<picture>\n"
        '  <source media="(prefers-color-scheme: dark)" srcset="assets/merged-dark.png">\n'
        f'  <img alt="Timeline of the merge dates of the pull requests listed below, one row per project, {win_en}." '
        'src="assets/merged-light.png" width="100%">\n'
        "</picture>\n\n"
        "| Project | What I fixed or built | Maintainer's words |\n"
        "|---|---|---|\n"
        f"{table}\n")

    lane_of_repo = {repo_of(m["url"]): m["lane"] for m in data["merged"]}
    notes = curated.get("open_notes", {})
    items = []
    for p in sort_open(open_pulls, data["lanes"], lane_of_repo):
        extra = [x for x in (notes.get(p["url"]), "approved" if p["review"] == "APPROVED" else None) if x]
        label = f"{short_label(p['repo'], data['lanes'], lane_of_repo)} #{p['number']}"
        items.append(f"[{label}]({p['url']})" + (f" ({', '.join(extra)})" if extra else ""))
    open_block = "\n" + (f"Open and under review: {', '.join(items)}." if items else "") + "\n"

    lines = []
    for pr in projects:
        facts = []
        if pr["release"]:
            facts.append(f"Latest release: [{pr['release']['tag']}]({pr['release']['url']}).")
        if pr["archived"]:
            facts.append(ARCHIVED["readme"])
        desc = f" — {pr['readme']}" if pr["readme"] else ""
        lines.append(f"- [{pr['name']}]({pr['url']}){desc}" + "".join(" " + f for f in facts))
    projects_block = "\n" + "\n".join(lines) + "\n"
    return {"merged": merged_block, "open": open_block, "projects": projects_block}


def sort_open(open_pulls: list[dict], lanes: list[dict], lane_of_repo: dict) -> list[dict]:
    return sorted(open_pulls, key=lambda p: (short_label(p["repo"], lanes, lane_of_repo).lower(), p["number"]))


def portfolio_blocks(data: dict, registry: list[dict], open_pulls: list[dict], projects: list[dict]) -> dict[str, str]:
    esc = htmlmod.escape
    blocks = {
        "data": (f'\n<script type="application/json" id="merged-data">{script_json(page_data(data))}</script>\n'
                 f'<script type="application/json" id="registry-data">{script_json(registry)}</script>\n'),
        "merged-count": str(len(data["merged"])),
        # Projets distincts ayant au moins une PR fusionnée (un dépôt = un projet), pour le fait « N projects ».
        "project-count": str(len({repo_of(m["url"]) for m in data["merged"]})),
        "range-en": esc(data["window"]["en"]),
        "range-fr": esc(data["window"]["fr"]),
        "range-en-dash": esc(data["window"]["en"].replace(" → ", "–")),
        "range-fr-dash": esc(data["window"]["fr"].replace(" → ", "–")),
    }
    lane_of_repo = {repo_of(m["url"]): m["lane"] for m in data["merged"]}
    for lang, lead, approved in (("en", "Open and under review: ", "approved"), ("fr", "En cours de revue : ", "approuvée")):
        # Même forme que le texte d'origine : « PyHealth #1187, #1202, #1207 » quand un projet a plusieurs PR.
        parts, prev = [], None
        for p in sort_open(open_pulls, data["lanes"], lane_of_repo):
            label = short_label(p["repo"], data["lanes"], lane_of_repo)
            item = (f"#{p['number']}" if label == prev else f"{esc(label)} #{p['number']}")
            parts.append(item + (f" ({approved})" if p["review"] == "APPROVED" else ""))
            prev = label
        blocks[f"open-{lang}"] = (lead + ", ".join(parts) + ".") if parts else ""
    for lang in ("en", "fr"):
        rows = []
        for pr in projects:
            what, evidence = pr[lang]
            facts = ([esc(pr["release"]["tag"])] if pr["release"] else []) + ([ARCHIVED[lang]] if pr["archived"] else [])
            evidence = " · ".join([e for e in [evidence] if e] + facts)
            rows.append(f'        <tr><td><a href="{esc(pr["url"])}" target="_blank" rel="noopener">{esc(pr["name"])}</a></td>'
                        f'<td>{what}</td><td class="mono">{evidence}</td></tr>')
        blocks[f"projects-{lang}"] = "\n" + "\n".join(rows) + "\n      "
    return blocks


def load_projects(snapshot: dict, report: dict) -> list[dict]:
    """Projets curés dans leur ordre, puis tout nouveau dépôt public (description GitHub telle quelle, signalée)."""
    cur = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    repos = {r["name"]: r for r in snapshot["repos"]}
    excluded = set(cur.get("exclude", []))
    out = []
    for p in cur["projects"]:
        r = repos.get(p["repo"])
        if r is None:
            report["projects"].append(f"{p['repo']} : absent des dépôts publics de {snapshot['login']} ; ligne conservée")
            r = {"url": f"https://github.com/{snapshot['login']}/{p['repo']}", "archived": False, "release": None}
        out.append({"name": p["repo"], "url": r["url"], "archived": r["archived"], "release": r["release"],
                     "readme": p["readme"], "en": p["en"], "fr": p["fr"]})
    curated_names = {p["repo"] for p in cur["projects"]}
    for name, r in sorted(repos.items()):
        if name in curated_names or name in excluded:
            continue
        desc = r["description"] or ""
        esc_desc = htmlmod.escape(desc)
        out.append({"name": name, "url": r["url"], "archived": r["archived"], "release": r["release"],
                    "readme": htmlmod.escape(desc, quote=False), "en": [esc_desc, ""], "fr": [esc_desc, ""]})
        report["projects"].append(f"{name} : nouveau dépôt public, affiché avec sa description GitHub ; "
                                  "texte à rédiger dans projects.json (ou ajouter le nom à \"exclude\")")
    return out


def marker_re(name: str) -> re.Pattern:
    return re.compile(r"(<!--\s*" + re.escape(name) + r":start\s*-->)(.*?)(<!--\s*" + re.escape(name) + r":end\s*-->)", re.S)


def replace_blocks(path: Path, text: str, blocks: dict[str, str]) -> str:
    for name, content in blocks.items():
        pat = marker_re(name)
        n = len(pat.findall(text))
        starts = len(re.findall(r"<!--\s*" + re.escape(name) + r":start\s*-->", text))
        ends = len(re.findall(r"<!--\s*" + re.escape(name) + r":end\s*-->", text))
        if n == 0 or n != starts or n != ends:
            sys.exit(f"{path} : marqueurs {name}:start / {name}:end absents ou déséquilibrés.")
        text = pat.sub(lambda m: m.group(1) + content + m.group(3), text)
    return text


def sync_file(path: Path, blocks: dict[str, str], check: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    new = replace_blocks(path, text, blocks)
    rel = path.relative_to(ROOT)
    if new == text:
        print(f"{rel} : blocs générés à jour")
        return True
    if check:
        print(f"{rel} : blocs générés périmés (lancer python visuals/build.py)")
        return False
    path.write_text(new, encoding="utf-8", newline="\n")
    print(f"{rel} : blocs générés réécrits")
    return True


def find_chrome() -> str:
    candidates = [os.environ.get("CHROME"),
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")]
    for c in candidates:
        if c and Path(c).exists():
            return c
    sys.exit("Chrome introuvable : définir la variable CHROME.")


def render(data: dict, registry: list[dict], groups: set[str], force: bool) -> None:
    tokens = (TEMPLATES / "tokens.css").read_text(encoding="utf-8")
    data_js = f"const DATA={script_json(page_data(data))};const REG={script_json(registry)};"
    hashes = json.loads(RENDER_HASHES.read_text(encoding="utf-8")) if RENDER_HASHES.exists() else {}
    chrome = None
    with tempfile.TemporaryDirectory() as tmp:
        for group, tpl, theme, out, w, h, scale in RENDERS:
            if group not in groups:
                continue
            if h is None:
                h = MERGED_BASE_HEIGHT + MERGED_LANE_HEIGHT * len(data["lanes"])
            html = (TEMPLATES / tpl).read_text(encoding="utf-8")
            for marker in ("/*TOKENS*/", "/*DATA*/"):
                if html.count(marker) != 1:
                    sys.exit(f"{tpl} : marqueur {marker} absent ou dupliqué.")
            html = html.replace("/*TOKENS*/", tokens).replace("/*DATA*/", data_js).replace("__THEME__", theme)
            key = f"{tpl}:{theme}"
            digest = hashlib.sha256(f"{w}x{h}@{scale}\n{html}".encode("utf-8")).hexdigest()
            if not force and hashes.get(key) == digest and out.exists():
                print(f"image : {out.relative_to(ROOT)} inchangée")
                continue
            chrome = chrome or find_chrome()
            page = Path(tmp) / f"{out.stem}.html"
            page.write_text(html, encoding="utf-8")
            out.parent.mkdir(parents=True, exist_ok=True)
            args = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    f"--user-data-dir={Path(tmp) / 'profile'}",
                    f"--window-size={w},{h}", f"--force-device-scale-factor={scale}",
                    f"--virtual-time-budget={CHROME_TIME_BUDGET_MS}", f"--screenshot={out}", page.as_uri()]
            if tpl != "social.html":
                args.insert(1, "--default-background-color=00000000")  # fond transparent pour les README
            subprocess.run(args, capture_output=True, check=True)
            if not out.exists() or out.stat().st_size == 0:
                sys.exit(f"capture vide : {out}")
            hashes[key] = digest
            print(f"image : {out.relative_to(ROOT)} ({out.stat().st_size // 1024} Ko)")
    RENDER_HASHES.write_text(json.dumps(hashes, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def hand_written_mentions(url: str, number: int, generated: list[re.Pattern]) -> tuple[list[str], list[str]]:
    """Lignes écrites à la main (hors blocs générés) qui citent une PR : par URL (sûr) ou par « #numéro » (possible)."""
    sure, maybe = [], []
    files = [README, PORTFOLIO, ENTRIES_JS, ROOT / "silent-failures" / "README.md"]
    bare = re.compile(r"#" + str(number) + r"\b")
    for f in files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        for pat in generated:  # le contenu généré est mis à jour automatiquement : on ne le signale pas
            text = pat.sub(lambda m: m.group(1) + "\n" * m.group(2).count("\n") + m.group(3), text)
        for i, line in enumerate(text.splitlines(), 1):
            where = f"{f.relative_to(ROOT).as_posix()}:{i}"
            if url in line:
                sure.append(where)
            elif bare.search(line):
                maybe.append(where)
    return sure, maybe


def write_report(path: Path, report: dict, changes: list[dict], snapshot: dict) -> None:
    pulls = {p["url"]: p for p in snapshot["pulls"]}
    generated = [marker_re(n) for n in ("merged", "open", "projects", "data", "merged-count", "project-count", "range-en", "range-fr",
                                        "range-en-dash", "range-fr-dash", "open-en", "open-fr", "projects-en", "projects-fr")]
    out = []
    if changes:
        out.append("## Changements relevés sur GitHub\n")
        out.append("Les blocs générés sont déjà à jour. Les lignes citées ci-dessous sont du texte écrit à la main "
                   "qui mentionne l'élément : à relire, car elles peuvent être devenues fausses.\n")
        for c in changes:
            if c["kind"].startswith("pull-"):
                p = pulls.get(c["url"], {})
                label = f"{p.get('repo', repo_of(c['url']))} #{p.get('number', c['url'].rsplit('/', 1)[-1])}"
                what = {"pull-new": f"nouvelle PR ({c.get('state')})",
                        "pull-state": f"{c.get('from')} → {c.get('to')}",
                        "pull-review": f"revue {c.get('from')} → {c.get('to')}",
                        "pull-gone": f"introuvable ou devenue privée sur GitHub (était {c.get('from')}), retirée de l'affichage"}[c["kind"]]
                sure, maybe = hand_written_mentions(c["url"], int(c["url"].rstrip("/").rsplit("/", 1)[-1]), generated)
                line = f"- [{label}]({c['url']}) : {what}"
                if sure:
                    line += f". Citée : {', '.join(f'`{s}`' for s in sure)}"
                if maybe:
                    line += f". Peut-être citée (même numéro) : {', '.join(f'`{s}`' for s in maybe)}"
                out.append(line)
            elif c["kind"] == "repo-new":
                out.append(f"- {c['url']} : nouveau dépôt public")
            else:
                out.append(f"- {c['url']} : {c['kind'].removeprefix('repo-')} "
                           f"{json.dumps(c.get('from'), ensure_ascii=False)} → {json.dumps(c.get('to'), ensure_ascii=False)}")
        out.append("")
    if report["pending"]:
        out.append("## PR fusionnées affichées avec leur titre GitHub, texte à rédiger\n")
        out.append("À ajouter dans `visuals/data/merged.json` (champs `en`, `fr`, `readme.text`, `readme.quote`, `sf`). "
                   "Squelette prêt à compléter :\n")
        out.append("```json")
        for p in report["pending"]:
            out.append(json.dumps({"date": p["date"], "lane": p["lane"], "ref": p["ref"], "url": p["url"], "sf": [],
                                   "en": p["title"], "fr": "", "readme": {"label": p["ref"], "text": p["title"], "quote": "merged"}},
                                  ensure_ascii=False) + ",")
        out.append("```\n")
    if report["dates"]:
        out.append("## Dates de fusion : merged.json diffère de GitHub\n")
        out.append("La date de merged.json reste affichée ; GitHub donne la date UTC de fusion.\n")
        out += [f"- [{d['ref']}]({d['url']}) : merged.json {d['curated']}, GitHub {d['github']}" for d in report["dates"]]
        out.append("")
    if report["projects"]:
        out.append("## Projets personnels\n")
        out += [f"- {x}" for x in report["projects"]]
        out.append("")
    body = "\n".join(out) if out else "Rien à relire.\n"
    path.write_text(body, encoding="utf-8", newline="\n")
    print(f"rapport : {path} ({'rien à relire' if not out else 'éléments à relire'})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="vérifie les blocs générés sans rien écrire")
    ap.add_argument("--images", choices=["all", "merged", "none"], default="all", help="images à (re)générer")
    ap.add_argument("--no-images", action="store_true", help="équivaut à --images none")
    ap.add_argument("--force-images", action="store_true", help="re-rend les images même si leurs entrées n'ont pas changé")
    ap.add_argument("--report", type=Path, help="écrit la liste « à relire » (Markdown)")
    ap.add_argument("--changes", type=Path, help="transitions produites par fetch_github.py --changes")
    args = ap.parse_args()

    report = {"pending": [], "dates": [], "projects": []}
    registry = load_registry()
    curated = load_curated({e["id"] for e in registry})
    snapshot = load_snapshot()
    data, open_pulls = assemble(curated, snapshot, report)
    projects = load_projects(snapshot, report)

    ok = sync_file(README, readme_blocks(data, open_pulls, curated, projects), check=args.check)
    ok = sync_file(PORTFOLIO, portfolio_blocks(data, registry, open_pulls, projects), check=args.check) and ok
    images = "none" if args.no_images or args.check else args.images
    if images != "none":
        render(data, registry, {"merged"}, args.force_images)
    for d in report["dates"]:
        print(f"  écart de date : {d['ref']} merged.json {d['curated']}, GitHub {d['github']}")
    for p in report["pending"]:
        print(f"  à rédiger : {p['ref']} ({p['date']}) affichée avec son titre GitHub")
    for x in report["projects"]:
        print(f"  projets : {x}")
    if args.report:
        changes = json.loads(args.changes.read_text(encoding="utf-8")) if args.changes and args.changes.exists() else []
        write_report(args.report, report, changes, snapshot)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
