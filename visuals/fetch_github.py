"""Relève sur GitHub l'état des pull requests de l'auteur et de ses dépôts publics, dans un instantané versionné.

Consomme :
  l'API GraphQL de GitHub, via la CLI `gh` (en local : `gh auth login` ; en CI : variable GH_TOKEN)
  visuals/data/merged.json   les PR curées dont l'auteur n'est pas GITHUB_LOGIN (ex. une revue dont l'auteur
                             de la PR a intégré nos commits) : leur état est relevé une par une

Produit :
  visuals/data/github.json   instantané trié par URL : PR (état, date de fusion, décision de revue) et dépôts
                             publics de l'auteur (description, archivage, dernière release)
  --changes FICHIER          (facultatif) transitions entre l'ancien et le nouvel instantané, en JSON, pour le
                             rapport « à relire » de build.py ; ce fichier n'est pas versionné

Hypothèses :
  - « Fusionnée » signifie mergedAt non nul selon GitHub ; la date retenue est la date UTC de mergedAt, comme
    les dates déjà saisies dans merged.json (vérifiées identiques le 2026-10-20).
  - Les PR vers des dépôts privés sont écartées : elles ne sont jamais affichées, et leur titre ne doit pas
    se retrouver dans un fichier publié. Les PR vers les dépôts de l'auteur lui-même ne sont pas « en amont ».
  - L'instantané ne contient pas d'horodatage de collecte : il ne change que si l'état GitHub change, ce qui
    évite un commit à chaque exécution planifiée.
  - La recherche GitHub plafonne à 1 000 résultats ; au-delà, le script échoue plutôt que de tronquer.
  - La recherche n'est pas exhaustive d'un jour à l'autre (constaté le 2026-10-21 : deux PR renvoyées la veille
    absentes des résultats, toujours présentes dans l'API). Toute PR déjà dans l'instantané précédent est donc
    relevée directement ; seule une PR vraiment introuvable (dépôt supprimé ou devenu privé) en sort, signalée.

Usage :
  python visuals/fetch_github.py
  python visuals/fetch_github.py --changes changes.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "visuals" / "data"
MERGED_JSON = DATA / "merged.json"
SNAPSHOT = DATA / "github.json"

GITHUB_LOGIN = "AxelNoun"
SEARCH_PAGE_SIZE = 100
SEARCH_LIMIT = 1000  # plafond documenté de la recherche GitHub

PR_FIELDS = """
  url number title state isDraft mergedAt reviewDecision
  repository { nameWithOwner isPrivate owner { login } }
  author { login }
"""

SEARCH_QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: %d, after: $cursor) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest { %s } }
  }
}
""" % (SEARCH_PAGE_SIZE, PR_FIELDS)

REPOS_QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 orderBy: {field: NAME, direction: ASC}) {
      totalCount
      nodes { name url description isArchived latestRelease { tagName url publishedAt } }
    }
  }
}
"""


def graphql(query: str, allow_not_found: bool = False, **variables: str) -> dict:
    gh = shutil.which("gh")
    if gh is None:
        sys.exit("CLI gh introuvable : https://cli.github.com (en CI, elle est préinstallée sur ubuntu-latest).")
    args = [gh, "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        if v is not None:
            args += ["-f", f"{k}={v}"]
    out = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    try:
        payload = json.loads(out.stdout)
    except json.JSONDecodeError:
        sys.exit(f"échec de l'appel GraphQL :\n{out.stderr.strip()}")
    errors = payload.get("errors") or []
    if allow_not_found:  # un dépôt supprimé ou devenu privé : l'alias vaut null, l'appelant le traite
        errors = [e for e in errors if e.get("type") != "NOT_FOUND"]
    if errors or payload.get("data") is None:
        sys.exit(f"erreurs GraphQL : {json.dumps(errors, ensure_ascii=False)}\n{out.stderr.strip()}")
    return payload["data"]


def pull_record(node: dict) -> dict:
    return {
        "url": node["url"],
        "repo": node["repository"]["nameWithOwner"],
        "number": node["number"],
        "title": node["title"],
        "state": node["state"],  # OPEN, MERGED ou CLOSED
        "draft": node["isDraft"],
        "merged": node["mergedAt"][:10] if node["mergedAt"] else None,
        "review": node["reviewDecision"],  # APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED ou null
        "by_author": (node.get("author") or {}).get("login") == GITHUB_LOGIN,
    }


def is_upstream_public(node: dict) -> bool:
    repo = node["repository"]
    return not repo["isPrivate"] and repo["owner"]["login"] != GITHUB_LOGIN


def search_pulls() -> list[dict]:
    q = f"author:{GITHUB_LOGIN} is:pr"
    nodes, cursor = [], None
    while True:
        res = graphql(SEARCH_QUERY, q=q, cursor=cursor)["search"]
        if res["issueCount"] > SEARCH_LIMIT:
            sys.exit(f"{res['issueCount']} PR : au-delà du plafond de recherche GitHub ({SEARCH_LIMIT}).")
        nodes += [n for n in res["nodes"] if n]
        if not res["pageInfo"]["hasNextPage"]:
            break
        cursor = res["pageInfo"]["endCursor"]
    return [pull_record(n) for n in nodes if is_upstream_public(n)]


def lookup_pulls(urls: list[str]) -> tuple[list[dict], list[str]]:
    """État de PR précises, hors recherche : renvoie (PR trouvées, URL introuvables ou devenues privées)."""
    if not urls:
        return [], []
    parts = []
    for i, url in enumerate(urls):
        owner, name, kind, number = url.rstrip("/").split("/")[-4:]
        if kind != "pull" or not number.isdigit():
            sys.exit(f"URL de PR inattendue : {url}")
        parts.append(f'p{i}: repository(owner: "{owner}", name: "{name}") {{ pullRequest(number: {number}) {{ {PR_FIELDS} }} }}')
    data = graphql("query {\n" + "\n".join(parts) + "\n}", allow_not_found=True)
    found, missing = [], []
    for i, url in enumerate(urls):
        node = (data.get(f"p{i}") or {}).get("pullRequest")
        if node is None or not is_upstream_public(node):
            missing.append(url)
        else:
            found.append(pull_record(node))
    return found, missing


def fetch_repos() -> list[dict]:
    repos = graphql(REPOS_QUERY, login=GITHUB_LOGIN)["user"]["repositories"]
    if repos["totalCount"] > 100:
        sys.exit("plus de 100 dépôts publics : ajouter la pagination à REPOS_QUERY.")
    out = []
    for r in repos["nodes"]:
        if r["name"] == GITHUB_LOGIN:
            continue  # le dépôt du README de profil lui-même
        rel = r["latestRelease"]
        out.append({
            "name": r["name"],
            "url": r["url"],
            "description": r["description"],
            "archived": r["isArchived"],
            "release": {"tag": rel["tagName"], "url": rel["url"], "date": rel["publishedAt"][:10]} if rel else None,
        })
    return out


def transitions(old: dict, new: dict) -> list[dict]:
    """Ce qui a changé sur GitHub depuis le dernier instantané : c'est ce qui peut périmer un texte écrit à la main."""
    changes = []
    old_pulls = {p["url"]: p for p in old.get("pulls", [])}
    for p in new["pulls"]:
        before = old_pulls.get(p["url"])
        if before is None:
            changes.append({"kind": "pull-new", "url": p["url"], "state": p["state"]})
        elif before["state"] != p["state"]:
            changes.append({"kind": "pull-state", "url": p["url"], "from": before["state"], "to": p["state"]})
        elif before["review"] != p["review"]:
            changes.append({"kind": "pull-review", "url": p["url"], "from": before["review"], "to": p["review"]})
    new_urls = {p["url"] for p in new["pulls"]}
    for url in sorted(set(old_pulls) - new_urls):
        changes.append({"kind": "pull-gone", "url": url, "from": old_pulls[url]["state"], "to": None})
    old_repos = {r["name"]: r for r in old.get("repos", [])}
    for r in new["repos"]:
        before = old_repos.get(r["name"])
        if before is None:
            changes.append({"kind": "repo-new", "url": r["url"]})
            continue
        for field in ("description", "archived", "release"):
            if before[field] != r[field]:
                changes.append({"kind": f"repo-{field}", "url": r["url"], "from": before[field], "to": r[field]})
    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--changes", type=Path, help="écrit les transitions depuis l'instantané précédent (JSON)")
    args = ap.parse_args()

    curated = json.loads(MERGED_JSON.read_text(encoding="utf-8"))
    old = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {}
    pulls = {p["url"]: p for p in search_pulls()}
    curated_urls = set(m["url"] for m in curated["merged"]) | set(curated.get("open_notes", {}))
    known = curated_urls | {p["url"] for p in old.get("pulls", [])}
    found, missing = lookup_pulls(sorted(known - set(pulls)))
    for p in found:
        pulls[p["url"]] = p
    if curated_urls & set(missing):
        sys.exit("PR curées introuvables ou devenues privées sur GitHub :\n  " + "\n  ".join(sorted(curated_urls & set(missing))))
    for url in missing:
        print(f"  PR sortie de l'instantané (introuvable ou devenue privée) : {url}")

    new = {"login": GITHUB_LOGIN,
           "pulls": sorted(pulls.values(), key=lambda p: p["url"]),
           "repos": sorted(fetch_repos(), key=lambda r: r["name"])}
    text = json.dumps(new, ensure_ascii=False, indent=1) + "\n"
    if SNAPSHOT.exists() and SNAPSHOT.read_text(encoding="utf-8") == text:
        print("instantané GitHub : inchangé")
    else:
        SNAPSHOT.write_text(text, encoding="utf-8", newline="\n")
        print(f"instantané GitHub : écrit ({len(new['pulls'])} PR, {len(new['repos'])} dépôts publics)")

    changes = transitions(old, new) if old else []
    if old and changes:
        for c in changes:
            print(f"  changement : {c['kind']} {c['url']}" + (f" ({c.get('from')} -> {c.get('to')})" if "to" in c else ""))
    if args.changes:
        args.changes.write_text(json.dumps(changes, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
