#!/usr/bin/env python3
"""Generate self-contained monochrome profile graphics from GitHub GraphQL."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
WIDTH = 620
LIGHT = {"ink": "#57606a", "strong": "#24292f", "muted": "#6e7781", "rule": "#d0d7de"}
DARK = {"ink": "#c9d1d9", "strong": "#f0f6fc", "muted": "#8b949e", "rule": "#30363d"}
QUERY = """
query Profile($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date weekday } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes { primaryLanguage { name } languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
        edges { size node { name } }
      }}
    }
  }
}
"""


def font_face(filename: str, weight: int) -> str:
    data = base64.b64encode((ASSETS / "fonts" / filename).read_bytes()).decode("ascii")
    return (
        f"@font-face{{font-family:ProfileMono;font-style:normal;font-weight:{weight};"
        f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
    )


def style() -> str:
    def rules(theme: dict[str, str]) -> str:
        return "".join(f".{name}{{fill:{color}}}" for name, color in theme.items()) + f".line{{stroke:{theme['ink']}}}"
    return (
        "<style>" + font_face("mono-regular.woff2", 400) + font_face("mono-bold.woff2", 600)
        + rules(LIGHT) + f"@media(prefers-color-scheme:dark){{{rules(DARK)}}}" + "</style>"
    )


def svg_open(height: int, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{title}" '
        'font-family="ProfileMono,monospace">' + style()
    )


def text(x: float, y: float, value: object, size: int, cls: str = "ink", *,
         anchor: str = "start", weight: int = 400, opacity: float | None = None) -> str:
    extra = f' opacity="{opacity}"' if opacity is not None else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" class="{cls}"{extra}>{value}</text>'
    )


def fade(delay: float) -> str:
    return f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="0.4s" fill="freeze"/>'


def fetch(login: str, token: str) -> dict:
    today = datetime.now(timezone.utc).date()
    payload = json.dumps({
        "query": QUERY,
        "variables": {
            "login": login,
            "from": f"{today - timedelta(days=364)}T00:00:00Z",
            "to": f"{today}T23:59:59Z",
        },
    }).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-readme"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise SystemExit(result["errors"])
    user = result.get("data", {}).get("user")
    if not user:
        raise SystemExit(f"GitHub user not found: {login}")
    return user


def fetch_public(login: str) -> dict:
    """Bootstrap local graphics from GitHub's public HTML/REST surfaces."""
    headers = {"User-Agent": "profile-readme", "Accept": "application/vnd.github+json"}
    with urllib.request.urlopen(
        urllib.request.Request(f"https://github.com/users/{login}/contributions", headers=headers), timeout=30
    ) as response:
        calendar_html = response.read().decode("utf-8")

    matches = re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*></td>\s*<tool-tip[^>]*>([^<]+)</tool-tip>',
        calendar_html,
    )
    days = []
    for iso, tooltip in matches:
        count_match = re.match(r"(\d+) contribution", tooltip)
        count = int(count_match.group(1)) if count_match else 0
        parsed = date.fromisoformat(iso)
        days.append({"date": iso, "contributionCount": count, "weekday": (parsed.weekday() + 1) % 7})
    if not days:
        raise SystemExit("Could not read the public GitHub contribution calendar")

    grouped: dict[date, list[dict]] = {}
    for day in days:
        parsed = date.fromisoformat(day["date"])
        sunday = parsed - timedelta(days=day["weekday"])
        grouped.setdefault(sunday, []).append(day)
    weeks = [{"contributionDays": sorted(grouped[key], key=lambda item: item["weekday"])} for key in sorted(grouped)]

    with urllib.request.urlopen(
        urllib.request.Request(f"https://api.github.com/users/{login}/repos?per_page=100&type=owner", headers=headers), timeout=30
    ) as response:
        repositories = json.load(response)
    nodes = []
    for repository in repositories:
        with urllib.request.urlopen(urllib.request.Request(repository["languages_url"], headers=headers), timeout=30) as response:
            language_bytes = json.load(response)
        edges = [
            {"size": size, "node": {"name": name}}
            for name, size in sorted(language_bytes.items(), key=lambda item: (-item[1], item[0]))
        ]
        primary = repository.get("language")
        nodes.append({"primaryLanguage": {"name": primary} if primary else None, "languages": {"edges": edges}})

    return {
        "contributionsCollection": {
            "contributionCalendar": {"totalContributions": sum(day["contributionCount"] for day in days), "weeks": weeks}
        },
        "repositories": {"nodes": nodes},
    }


def analyse(user: dict) -> dict:
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    days = [day for week in weeks for day in week["contributionDays"]]
    weekly = [sum(day["contributionCount"] for day in week["contributionDays"]) for week in weeks]

    runs: list[tuple[int, str | None, str | None]] = []
    length = 0
    start = None
    for day in days:
        if day["contributionCount"]:
            start = start or day["date"]
            length += 1
        elif length:
            runs.append((length, start, previous))
            length, start = 0, None
        previous = day["date"]
    if length:
        runs.append((length, start, days[-1]["date"]))
    longest = max(runs, default=(0, None, None), key=lambda item: item[0])
    current = runs[-1] if runs and runs[-1][2] in {days[-1]["date"], days[-2]["date"]} else (0, None, None)

    bytes_by_language: Counter[str] = Counter()
    repos_by_language: Counter[str] = Counter()
    for repository in user["repositories"]["nodes"]:
        if repository.get("primaryLanguage"):
            repos_by_language[repository["primaryLanguage"]["name"]] += 1
        for edge in repository["languages"]["edges"]:
            bytes_by_language[edge["node"]["name"]] += edge["size"]

    return {
        "total": calendar["totalContributions"], "weeks": weeks, "days": days, "weekly": weekly,
        "active": sum(bool(day["contributionCount"]) for day in days), "best_week": max(weekly, default=0),
        "current": current, "longest": longest,
        "bytes": bytes_by_language.most_common(5), "repos": repos_by_language.most_common(5),
    }


def stats_graph(data: dict) -> str:
    height, baseline, ceiling = 150, 140, 92
    weekly = data["weekly"] or [0]
    peak = max(weekly) or 1
    step = WIDTH / max(1, len(weekly) - 1)
    points = [(index * step, baseline - value / peak * (baseline - ceiling)) for index, value in enumerate(weekly)]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    fill = path + f" L{points[-1][0]:.1f},{baseline} L0,{baseline} Z"
    out = [svg_open(height, "GitHub contributions in the last year")]
    out += [f'<g opacity="0">{fade(0.05)}{text(0, 48, data["total"], 48, "strong", weight=600)}'
            f'{text(0, 70, "contributions / last year", 12, "muted")}</g>']
    for index, (value, label) in enumerate(((data["active"], "active days"), (data["best_week"], "best week"))):
        out.append(f'<g opacity="0">{fade(0.22 + index * .12)}{text(WIDTH, 28 + index * 38, value, 20, "strong", anchor="end", weight=600)}{text(WIDTH, 44 + index * 38, label, 11, "muted", anchor="end")}</g>')
    out.append('<clipPath id="chart"><rect x="0" y="84" width="0" height="66"><animate attributeName="width" from="0" to="620" begin=".45s" dur="1.25s" fill="freeze"/></rect></clipPath>')
    out.append(f'<g clip-path="url(#chart)"><path d="{fill}" class="ink" opacity=".12"/><path d="{path}" fill="none" class="line" stroke-width="2" stroke-linejoin="round"/></g>')
    out.append(f'<circle cx="{points[-1][0] - 2:.1f}" cy="{points[-1][1]:.1f}" r="4" class="strong" opacity="0">{fade(1.72)}</circle></svg>')
    return "".join(out)


def streak_graph(data: dict) -> str:
    out = [svg_open(92, "Current and longest contribution streaks")]
    out.append('<line x1="310" y1="12" x2="310" y2="80" class="line" opacity=".25"/>')
    for index, (run, label) in enumerate(((data["current"], "current streak"), (data["longest"], "longest streak"))):
        x = 26 if index == 0 else 336
        dates = "no active streak" if not run[0] else f"{run[1]}  /  {run[2]}"
        out.append(f'<g opacity="0">{fade(.1 + index * .15)}{text(x, 39, run[0], 32, "strong", weight=600)}{text(x, 59, label, 11, "muted")}{text(x, 76, dates, 9, "muted")}</g>')
    out.append("</svg>")
    return "".join(out)


def languages_graph(data: dict) -> str:
    out = [svg_open(148, "Top public repository languages")]
    groups = [(18, "BY BYTES", data["bytes"], True), (328, "BY REPOSITORY", data["repos"], False)]
    for group_index, (left, label, values, percentage) in enumerate(groups):
        out.append(text(left, 14, label, 9, "muted"))
        maximum = max((value for _, value in values), default=1)
        total = sum(value for _, value in values) or 1
        for row, (name, value) in enumerate(values):
            y = 28 + row * 23
            shown = f"{value / total:.0%}" if percentage else str(value)
            bar = 120 * value / maximum
            out.append(f'<g opacity="0">{fade(.18 + group_index * .08 + row * .05)}{text(left, y + 9, name.lower()[:12], 10, "strong")}{text(left + 276, y + 9, shown, 10, "muted", anchor="end")}</g>')
            out.append(f'<rect x="{left + 92}" y="{y + 2}" width="{bar:.1f}" height="7" rx="3.5" class="ink" opacity="0">{fade(.34 + row * .05)}</rect>')
    out.append("</svg>")
    return "".join(out)


def year_graph(data: dict) -> str:
    ramp = " .:+#@"
    out = [svg_open(142, "A year of contributions represented as characters")]
    out += [text(28, 17, "THE YEAR IN CHARACTERS", 9, "muted"), text(28, 35, f'{data["active"]} active days', 11, "strong")]
    for weekday in range(7):
        chars = "".join(ramp[min(5, next((day["contributionCount"] for day in week["contributionDays"] if day["weekday"] == weekday), 0))] for week in data["weeks"])
        out.append(f'<text x="28" y="{56 + weekday * 11}" font-size="9.5" class="ink" xml:space="preserve" opacity="0">{chars}{fade(.25 + weekday * .07)}</text>')
    out.append(text(592, 136, ". : + # @", 9, "muted", anchor="end"))
    out.append("</svg>")
    return "".join(out)


def heading_graph(label: str) -> str:
    end = min(260, 16 + len(label) * 10)
    return svg_open(28, label) + text(0, 19, label, 16, "strong", weight=600) + f'<line x1="{end}" y1="13" x2="620" y2="13" class="line" opacity=".28"/></svg>'


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    login = os.environ.get("GH_LOGIN", "praneettigga")
    ASSETS.mkdir(parents=True, exist_ok=True)
    data = analyse(fetch(login, token) if token else fetch_public(login))
    files = {
        "stats.svg": stats_graph(data), "streak.svg": streak_graph(data),
        "languages.svg": languages_graph(data), "year.svg": year_graph(data),
    }
    for label in ("about", "stack", "featured", "stats", "about this profile"):
        files[f"heading-{label.replace(' ', '-')}.svg"] = heading_graph(label)
    changed = []
    for filename, content in files.items():
        path = ASSETS / filename
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            changed.append(filename)
    print(f"{data['total']} contributions; updated: {', '.join(changed) if changed else 'nothing'}")


if __name__ == "__main__":
    main()
