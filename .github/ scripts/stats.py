#!/usr/bin/env python3
"""Builds stats.svg: a GitHub stats card in the same style as the other banners.

Usage:  python3 stats.py OUT_FILE
Env:    GH_USER        GitHub username            (default: Ayesha-98)
        DISPLAY_NAME   Name shown in the title    (default: Ayesha Majid)
        GH_TOKEN       Token for the GitHub API   (optional, needed for contributions)
        STATS_SAMPLE   Set to 1 to draw made-up numbers, for a design preview only
Uses the Python standard library only.
"""
import os, sys, json, html, datetime, urllib.request
from collections import Counter

OUT = sys.argv[1]
USER = os.environ.get("GH_USER", "Ayesha-98")
NAME = os.environ.get("DISPLAY_NAME", "Ayesha Majid")
TOKEN = os.environ.get("GH_TOKEN")
SAMPLE = os.environ.get("STATS_SAMPLE") == "1"

BG, PANEL, PANEL2 = "#0e1829", "#142238", "#1b2d48"
LINE, TEXT, MUTED = "#2d4668", "#e6eefb", "#8196b5"
BLUE, ICE, ORANGE, DIM = "#62aaff", "#cfe6ff", "#FF7036", "#61759a"
MONO = "'SFMono-Regular','JetBrains Mono',Consolas,'Courier New',monospace"
SANS = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
e = html.escape


def api(url, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    if SAMPLE:
        return dict(repos=6, followers=1, stars=0, contrib=42, since="2025",
                    langs=[("HTML", 3), ("C++", 1), ("CSS", 1), ("JavaScript", 1)])
    d = dict(repos=None, followers=None, stars=None, contrib=None, since=None, langs=[])
    try:
        p = api(f"https://api.github.com/users/{USER}")
        d["repos"], d["followers"] = p.get("public_repos"), p.get("followers")
        d["since"] = (p.get("created_at") or "")[:4] or None
    except Exception as ex:
        print("profile fetch failed:", ex)
    try:
        repos = []
        for page in (1, 2, 3):
            chunk = api(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}")
            repos += chunk
            if len(chunk) < 100:
                break
        own = [r for r in repos if not r.get("fork")]
        d["stars"] = sum(r.get("stargazers_count", 0) for r in own)
        d["langs"] = Counter(r["language"] for r in own if r.get("language")).most_common(5)
    except Exception as ex:
        print("repo fetch failed:", ex)
    if TOKEN:
        try:
            q = {"query": 'query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{totalContributions}}}}',
                 "variables": {"u": USER}}
            r = api("https://api.github.com/graphql", q)
            d["contrib"] = r["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        except Exception as ex:
            print("contribution fetch failed:", ex)
    return d


def fmt(v):
    return "—" if v is None else f"{v:,}"


def icon(kind):
    s = f'stroke="{BLUE}" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    paths = {
        "repo": '<path d="M-14 -9 h10 l4 5 h14 v17 h-28 Z"/>',
        "people": '<circle cx="0" cy="-5" r="6"/><path d="M-13 14 q0 -12 13 -12 q13 0 13 12"/>',
        "star": '<path d="M0 -15 L4.4 -5 L15 -4 L7 3 L9.5 14 L0 8.5 L-9.5 14 L-7 3 L-15 -4 L-4.4 -5 Z"/>',
        "bars": '<path d="M-13 13 V3 M-4.5 13 V-6 M4.5 13 V0 M13 13 V-14"/>',
    }
    return f'<g {s}>{paths[kind]}</g>'


def build(d):
    tiles = [("repo", fmt(d["repos"]), "public repos"),
             ("people", fmt(d["followers"]), "followers"),
             ("star", fmt(d["stars"]), "stars earned"),
             ("bars", fmt(d["contrib"]), "contributions · last year")]
    tx = ""
    for i, (ic, val, label) in enumerate(tiles):
        x = 84 + i * 364
        tx += f"""  <g transform="translate({x},190)"><g style="animation: rise .7s ease-out {0.2+i*0.15:.2f}s both">
    <rect width="340" height="150" rx="22" fill="{PANEL}" stroke="{LINE}" stroke-width="2"/>
    <rect x="24" y="24" width="52" height="52" rx="14" fill="{PANEL2}"/>
    <g transform="translate(50,50)">{icon(ic)}</g>
    <text class="sans" x="24" y="118" font-size="42" font-weight="800" fill="{TEXT}">{e(val)}</text>
    <text class="mono" x="24" y="140" font-size="14" fill="{ORANGE}">{e(label)}</text>
  </g></g>
"""
    langs = d["langs"]
    total = sum(n for _, n in langs)
    colors = [BLUE, ORANGE, ICE, "#3d6fb3", "#8196b5"]
    bar = legend = ""
    if total:
        x0, w = 28, 1432 - 56
        cx = x0
        lx = 28
        for i, (lang, n) in enumerate(langs):
            seg = round(w * n / total, 1)
            c = colors[i % len(colors)]
            bar += f'<rect x="{cx}" y="58" width="{seg}" height="18" fill="{c}"/>'
            cx += seg
            pct = round(100 * n / total)
            legend += (f'<circle cx="{lx+6}" cy="116" r="6" fill="{c}"/>'
                       f'<text class="mono" x="{lx+20}" y="121" font-size="16" fill="{SOFT}">{e(lang)} {pct}%</text>')
            lx += 40 + 10 * len(f"{lang} {pct}%")
        bar = f'<clipPath id="barclip"><rect x="{x0}" y="58" width="{w}" height="18" rx="9"/></clipPath><g clip-path="url(#barclip)">{bar}</g>'
    else:
        msg = ("Could not reach GitHub on this run. The next daily refresh will fill this in."
               if d["repos"] is None else "No public code yet. The first repos will show up here.")
        legend = f'<text class="mono" x="28" y="116" font-size="16" fill="{MUTED}">{msg}</text>'
    since = f" · on GitHub since {d['since']}" if d["since"] else ""
    note = "sample numbers, design preview only" if SAMPLE else f"updated {datetime.date.today().isoformat()} · refreshes daily{since}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="570" viewBox="0 0 1600 570" role="img" aria-label="{e(NAME)}'s GitHub stats">
  <style>
    .mono {{ font-family: {MONO}; }}
    .sans {{ font-family: {SANS}; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(18px); }} to {{ opacity: 1; transform: none; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>
  <rect width="1600" height="570" rx="36" fill="{BG}"/>
  <rect x="1" y="1" width="1598" height="568" rx="36" fill="none" stroke="{LINE}" stroke-opacity=".6" stroke-width="2"/>
  <text class="mono" x="84" y="84" font-size="20" fill="{ORANGE}" letter-spacing="5">ACTIVITY</text>
  <text class="sans" x="84" y="152" font-size="58" font-weight="800" fill="{TEXT}" letter-spacing="-1.5">{e(NAME)}'s GitHub Stats</text>
{tx}  <g transform="translate(84,364)"><g style="animation: rise .7s ease-out .85s both">
    <rect width="1432" height="150" rx="22" fill="{PANEL}" stroke="{LINE}" stroke-width="2"/>
    <text class="mono" x="28" y="38" font-size="15" fill="{ORANGE}">top languages · by public repo</text>
    {bar}
    {legend}
  </g></g>
  <text class="mono" x="84" y="548" font-size="16" fill="{MUTED}">{e(note)}</text>
</svg>
"""


SOFT = "#b9c8de"
if __name__ == "__main__":
    data = collect()
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(data))
    print("wrote", OUT, data)
