"""Refresh the live parts of the profile from the GitHub API (run daily by .github/workflows/live.yml).

- assets/stats-dark.svg     merged-PR count and number of upstream projects
- assets/activity-dark.svg  last 12 months of contributions, drawn as a spike raster
- README.md                 <!-- live:start --> latest merges, <!-- open:start --> PRs in review

Needs GH_TOKEN (the workflow passes github.token). Standard library only.
If a request fails, the previous file is kept and the run still succeeds.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import make_animations  # noqa: E402
import make_assets  # noqa: E402

USER = os.environ.get("PROFILE_USER", "AxelNoun")
ROOT = os.path.join(os.path.dirname(__file__), "..")
README = os.path.join(ROOT, "README.md")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def api(url: str, body: dict | None = None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USER}-profile-live")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search(q: str) -> list[dict]:
    items, page = [], 1
    while True:
        url = "https://api.github.com/search/issues?" + urllib.parse.urlencode({"q": q, "per_page": 100, "page": page})
        data = api(url)
        items += data["items"]
        if len(items) >= data["total_count"] or not data["items"] or page >= 10:
            return items
        page += 1


def repo_of(item: dict) -> str:
    return item["repository_url"].split("/repos/", 1)[1]


def replace_block(text: str, name: str, body: str) -> str:
    pat = re.compile(r"(<!--\s*" + name + r":start\s*-->)(.*?)(<!--\s*" + name + r":end\s*-->)", re.S)
    if not pat.search(text):
        print(f"marker {name} missing, skipped")
        return text
    return pat.sub(lambda m: m.group(1) + "\n" + body.strip() + "\n" + m.group(3), text)


def md(s: str) -> str:
    return s.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def main() -> None:
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    readme = open(README, encoding="utf-8").read()

    # ---- merged upstream PRs
    try:
        merged = search(f"is:pr author:{USER} is:merged -user:{USER}")
        merged.sort(key=lambda i: i.get("closed_at") or "", reverse=True)
        repos = sorted({repo_of(i) for i in merged})
        print(f"merged: {len(merged)} PRs in {len(repos)} repos")
        make_assets.STATS[0] = (str(len(merged)), "", "pull requests merged upstream", f"live count · updated {today}")
        make_assets.STATS[1] = (str(len(repos)), "", "open-source projects", " · ".join(r.split("/")[1] for r in repos[:4]) + " · …")
        with open(os.path.join(make_assets.OUT, "stats-dark.svg"), "w") as f:
            f.write(make_assets.stats("dark"))
        lines = []
        for i in merged[:5]:
            date = (i.get("closed_at") or "")[:10]
            lines.append(f"- `{date}` **[{repo_of(i)} #{i['number']}]({i['html_url']})**: {md(i['title'])}")
        readme = replace_block(readme, "live", "\n".join(lines) + f"\n\n<sub>Refreshed daily by GitHub Actions · last run {today}</sub>")
    except Exception as e:  # keep the previous version
        print("merged PRs: skipped:", e)

    # ---- open PRs in review
    try:
        opened = search(f"is:pr author:{USER} is:open -user:{USER} archived:false")
        opened.sort(key=lambda i: i.get("updated_at") or "", reverse=True)
        print(f"open: {len(opened)}")
        if opened:
            parts = [f"[{repo_of(i).split('/')[1]} #{i['number']}]({i['html_url']}) {md(i['title'])}" for i in opened[:8]]
            search_open = f"https://github.com/search?q=is%3Apr+author%3A{USER}+is%3Aopen+-user%3A{USER}&type=pullrequests"
            more = f"\n\n[… and {len(opened) - 8} more]({search_open})" if len(opened) > 8 else ""
            body = f"**In review right now ({len(opened)}):**\n\n" + "\n".join(f"- {p}" for p in parts) + more
        else:
            body = "_No pull request in review right now._"
        readme = replace_block(readme, "open", body)
    except Exception as e:
        print("open PRs: skipped:", e)

    # ---- contribution calendar
    try:
        q = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
               totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
        data = api("https://api.github.com/graphql", {"query": q, "variables": {"login": USER}})
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = [{"date": d["date"], "count": d["contributionCount"]} for w in cal["weeks"] for d in w["contributionDays"]]
        with open(os.path.join(make_assets.OUT, "activity-dark.svg"), "w") as f:
            f.write(make_animations.activity("dark", days, cal["totalContributions"], today))
        print(f"activity: {cal['totalContributions']} contributions")
    except Exception as e:
        print("activity: skipped:", e)

    open(README, "w", encoding="utf-8").write(readme)


if __name__ == "__main__":
    main()
