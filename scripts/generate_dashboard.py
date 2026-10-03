#!/usr/bin/env python3
"""Builds id-dashboard.svg from live GitHub data (stdlib only).

env:  USERNAME      GitHub login (default: Rajnishmishra10)
      GITHUB_TOKEN  token (set automatically in GitHub Actions)
      DASH_FIXTURE  optional JSON file with {"repos":[...]} to skip the REST call (offline testing)
"""
import base64, json, math, os, random, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

USER = os.environ.get("USERNAME", "Rajnishmishra10")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "id-dashboard.svg")
NAME, ROLE = "RAJNISH", "FULL STACK DEV"
NOW = [("LEARNING", "New technologies, tools and frameworks", "#22d3ee"),
       ("BUILDING", "Projects, line by line", "#a78bfa"),
       ("EXPLORING", "What to build and learn next", "#f472b6")]
DUR = 12

def http(url, data=None, auth=True):
    h = {"User-Agent": "id-dashboard", "Accept": "application/vnd.github+json"}
    if auth and TOKEN: h["Authorization"] = f"Bearer {TOKEN}"
    if data is not None: h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h)
    return urllib.request.urlopen(req, timeout=30).read().decode()

# ---------------- data ----------------
def get_repos():
    fx = os.environ.get("DASH_FIXTURE")
    if fx: return json.load(open(fx))["repos"]
    out, page = [], 1
    while True:
        chunk = json.loads(http(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}"))
        out += chunk
        if len(chunk) < 100: return out
        page += 1

def days_graphql():
    q = ("query($l:String!){user(login:$l){contributionsCollection{totalCommitContributions "
         "contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}")
    r = json.loads(http("https://api.github.com/graphql", json.dumps({"query": q, "variables": {"l": USER}}).encode()))
    c = r["data"]["user"]["contributionsCollection"]
    days = {d["date"]: d["contributionCount"] for w in c["contributionCalendar"]["weeks"] for d in w["contributionDays"]}
    return c["totalCommitContributions"], days

def days_scrape():
    html = http(f"https://github.com/users/{USER}/contributions", auth=False)
    ids = {i: d for d, i in re.findall(r'data-date="(\d{4}-\d\d-\d\d)"[^>]*?id="(contribution-day-component-\d+-\d+)"', html)}
    days = {}
    for i, n in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>\s*(No|\d[\d,]*) contributions? on', html):
        if i in ids: days[ids[i]] = 0 if n == "No" else int(n.replace(",", ""))
    return sum(days.values()), days

def streak(days):
    d = datetime.now(timezone.utc).date()
    if not days.get(d.isoformat()): d -= timedelta(days=1)
    n = 0
    while days.get(d.isoformat(), 0) > 0:
        n += 1; d -= timedelta(days=1)
    return n

repos = [r for r in get_repos() if not r.get("fork")]
stars_total = sum(r["stargazers_count"] for r in repos)
chart = [r for r in repos if not r.get("archived") and r["name"].lower() != USER.lower()]

def repo_langs(r):
    if "_languages" in r: return r["_languages"]          # offline fixture
    try: return json.loads(http(r["languages_url"]))
    except Exception as e:
        print("languages failed for", r["name"], e, file=sys.stderr); return {}

count, size = {}, {}
for r in chart:
    for lang, nbytes in repo_langs(r).items():
        count[lang] = count.get(lang, 0) + 1
        size[lang] = size.get(lang, 0) + nbytes
top = sorted(count, key=lambda l: (-count[l], -size[l]))[:5]
REPOS = [(l if len(l) <= 15 else l[:14] + "…", count[l]) for l in top]

try:
    commits, days = days_graphql() if TOKEN else days_scrape()
except Exception as e:
    print("graphql failed, falling back to scrape:", e, file=sys.stderr)
    commits, days = days_scrape()
KPIS = [("REPOS", len(repos), "#22d3ee"), ("COMMITS", commits, "#f472b6"), ("DAY STREAK", streak(days), "#fbbf24")]
print("KPIs:", KPIS, "\nREPOS:", REPOS)

# ---------------- svg ----------------
PORTRAIT = base64.b64encode(open(os.path.join(ROOT, "assets", "portrait.jpg"), "rb").read()).decode()

A = 6.0; pts = [(0, 0.0), (0.5, 0.0)]; t = 0.6
while t <= 10.6:
    tp = t - 0.6
    pts.append((t, A * math.exp(-tp / 2.4) * math.cos(2 * math.pi * tp / 2.3))); t = round(t + 0.1, 2)
pts += [(10.7, 0.0), (DUR, 0.0)]
rot_vals = ";".join(f"{a:.2f} 160 -20" for _, a in pts)
rot_keys = ";".join(f"{tt / DUR:.4f}" for tt, _ in pts)

random.seed(7); x = 0; bars = []
while x < 142:
    w = random.choice([1, 1, 2, 3]); g = random.choice([1, 2, 2])
    if x + w > 144: break
    bars.append(f'<rect x="{88 + x}" y="362" width="{w}" height="26"/>'); x += w + g
barcode = "".join(bars)

def reel(final, col):
    vals = []
    for i in range(10):
        v = round(final * (1 - (1 - i / 9) ** 3))
        if not vals or v != vals[-1]: vals.append(v)
    vals[-1] = final; n = len(vals)
    txt = "".join(f'<text x="0" y="{27 + 36 * k}" font-size="28" font-weight="800" class="m" fill="{col}">{v}</text>' for k, v in enumerate(vals))
    if n == 1: return f'<g clip-path="url(#kc)">{txt}</g>'
    tv = ";".join(f"0 {-36 * k}" for k in range(n))
    tk = ";".join(f"{(0.004 + k * 0.017):.3f}" if k else "0" for k in range(n))
    return (f'<g clip-path="url(#kc)"><g><animateTransform attributeName="transform" type="translate" calcMode="discrete" '
            f'values="{tv}" keyTimes="{tk}" dur="{DUR}s" repeatCount="indefinite"/>{txt}</g></g>')

tiles = ""
for i, (lab, val, col) in enumerate(KPIS):
    tiles += (f'<g transform="translate({24 + i * 175},54)"><rect width="162" height="72" rx="12" fill="#14162a" stroke="{col}" stroke-opacity=".45"/>'
              f'<rect x="12" y="12" width="14" height="3" rx="1.5" fill="{col}"/><text x="12" y="30" font-size="9" letter-spacing="2" fill="#9aa0b4" class="m">{lab}</text>'
              f'<g transform="translate(12,32)">{reel(val, col)}</g></g>')

mx = max([v for _, v in REPOS] + [1]); bars_svg = ""
for i, (nm, v) in enumerate(REPOS):
    y0 = 198 + i * 32; w = max(round(76 * v / mx, 1), 8); s0 = 0.02 + 0.02 * i; e = s0 + 0.1
    kt = f"0;{s0:.3f};{e:.3f};1"
    nm = nm.replace("&", "&amp;").replace("<", "&lt;")
    bars_svg += (f'<text x="40" y="{y0 + 11}" font-size="11" fill="#e6e8f2" class="m">{nm}</text>'
                 f'<rect x="146" y="{y0}" width="76" height="14" rx="7" fill="#1b1e38"/>'
                 f'<rect x="146" y="{y0}" width="0" height="14" rx="7" fill="#22d3ee"><animate attributeName="width" values="0;0;{w};{w}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/></rect>'
                 f'<text x="154" y="{y0 + 11}" font-size="11" font-weight="700" fill="#22d3ee" class="m" opacity="0"><animate attributeName="x" values="154;154;{146 + w + 8};{146 + w + 8}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;0;1;1" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>{v}</text>')

hint = ""
if not REPOS:
    hint = ('<text x="40" y="350" font-size="9" letter-spacing="1" fill="#6b7190" class="m">NO LANGUAGES DETECTED YET</text>'
            '<text x="40" y="364" font-size="9" letter-spacing="1" fill="#6b7190" class="m">BARS APPEAR AS YOU ADD PROJECTS</text>')

def wrap(t, n=40):
    lines, cur = [], ""
    for w_ in t.split():
        if len(cur) + len(w_) + 1 > n and cur: lines.append(cur); cur = w_
        else: cur = (cur + " " + w_).strip()
    return lines + [cur]

now_svg = ""
for i, (lab, txt, col) in enumerate(NOW):
    y = 196 + i * 50
    now_svg += (f'<rect x="288" y="{y}" width="84" height="22" rx="11" fill="{col}" fill-opacity=".12" stroke="{col}" stroke-opacity=".5"/>'
                f'<text x="330" y="{y + 15}" font-size="9" letter-spacing="1.5" text-anchor="middle" fill="{col}" class="m">{lab}</text>')
    for j, ln in enumerate(wrap(txt)):
        now_svg += f'<text x="288" y="{y + 38 + j * 17}" font-size="12" fill="#e6e8f2">{ln}</text>'

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 420" width="900" height="420" role="img" aria-label="ID badge and developer dashboard">
<defs>
<linearGradient id="aa" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#22d3ee"/><stop offset=".5" stop-color="#a78bfa"/><stop offset="1" stop-color="#f472b6"/></linearGradient>
<linearGradient id="ab" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee" stop-opacity=".7"/><stop offset=".5" stop-color="#a78bfa" stop-opacity=".35"/><stop offset="1" stop-color="#f472b6" stop-opacity=".7"/></linearGradient>
<pattern id="ad" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1" fill="#fff" fill-opacity=".05"/></pattern>
<linearGradient id="sg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2a2466"/><stop offset=".5" stop-color="#4c3fb5"/><stop offset="1" stop-color="#2a2466"/></linearGradient>
<linearGradient id="mg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3f4f6"/><stop offset=".5" stop-color="#9ca3af"/><stop offset="1" stop-color="#4b5563"/></linearGradient>
<linearGradient id="cg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fde68a"/><stop offset=".5" stop-color="#f59e0b"/><stop offset="1" stop-color="#b45309"/></linearGradient>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1f40"/><stop offset="1" stop-color="#0f1020"/></linearGradient>
<linearGradient id="hf" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".25" stop-color="#22d3ee" stop-opacity=".35"/><stop offset=".5" stop-color="#a78bfa" stop-opacity=".4"/><stop offset=".75" stop-color="#f472b6" stop-opacity=".35"/><stop offset="1" stop-color="#fbbf24" stop-opacity="0"/></linearGradient>
<clipPath id="lc"><rect width="900" height="420" rx="22"/></clipPath>
<clipPath id="bc"><rect x="70" y="126" width="180" height="274" rx="16"/></clipPath>
<clipPath id="pc"><rect x="112" y="154" width="96" height="96" rx="12"/></clipPath>
<clipPath id="kc"><rect x="0" y="0" width="100" height="34"/></clipPath>
<style>text{{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif}}.m{{font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace}}</style>
</defs>

<g><rect width="900" height="420" rx="22" fill="#0d0e16"/><rect width="900" height="420" rx="22" fill="url(#ad)"/>
<g clip-path="url(#lc)">
<g><animateTransform attributeName="transform" type="translate" calcMode="spline" values="0 -520;0 14;0 0;0 0" keyTimes="0;0.05;0.065;1" keySplines=".5 0 1 1;.2 0 .4 1;0 0 1 1" dur="{DUR}s" repeatCount="indefinite"/>
<g><animateTransform attributeName="transform" type="rotate" values="{rot_vals}" keyTimes="{rot_keys}" dur="{DUR}s" repeatCount="indefinite"/>
<rect x="142" y="-30" width="36" height="100" fill="url(#sg)"/>
<path d="M145 -30V70M175 -30V70" stroke="#fff" stroke-opacity=".22" stroke-dasharray="3 3" fill="none"/>
<text transform="translate(165,6) rotate(90)" font-size="9" letter-spacing="2" fill="#d9dcff" fill-opacity=".85" class="m" textLength="58" lengthAdjust="spacing">RAJNISH •</text>
<g transform="translate(0,-30)"><rect x="148" y="98" width="24" height="9" rx="3" fill="url(#mg)"/>
<circle cx="160" cy="122" r="11" fill="none" stroke="url(#mg)" stroke-width="3.5"/>
<rect x="70" y="126" width="180" height="274" rx="16" fill="url(#bg)"/>
<rect x="70.75" y="126.75" width="178.5" height="272.5" rx="15.5" fill="none" stroke="url(#ab)" stroke-width="1.5"/>
<rect x="140" y="130" width="40" height="8" rx="4" fill="#0d0e16" stroke="#2a2d4a"/>
<rect x="108" y="150" width="104" height="104" rx="16" fill="#e8e6ff"/>
<image href="data:image/jpeg;base64,{PORTRAIT}" x="112" y="154" width="96" height="96" preserveAspectRatio="xMidYMid slice" clip-path="url(#pc)"/>
<rect x="108" y="150" width="104" height="104" rx="16" fill="none" stroke="#a78bfa" stroke-opacity=".6" stroke-width="1.5"/>
<rect x="108" y="150" width="104" height="104" rx="16" fill="none" stroke="#22d3ee" stroke-opacity=".35" stroke-width="7" pathLength="100" stroke-dasharray="14 86" stroke-linecap="round"><animate attributeName="stroke-dashoffset" values="0;-100" dur="2.8s" repeatCount="indefinite"/></rect>
<rect x="108" y="150" width="104" height="104" rx="16" fill="none" stroke="#fff" stroke-width="2.5" pathLength="100" stroke-dasharray="14 86" stroke-linecap="round"><animate attributeName="stroke-dashoffset" values="0;-100" dur="2.8s" repeatCount="indefinite"/></rect>
<text x="160" y="280" font-size="20" font-weight="800" text-anchor="middle" fill="#e6e8f2" letter-spacing="2">{NAME}</text>
<text x="160" y="297" font-size="8.5" letter-spacing="3" text-anchor="middle" fill="#22d3ee" class="m">{ROLE}</text>
<path d="M88 310h144" stroke="#2a2d4a"/>
<g transform="translate(88,322)"><rect width="36" height="28" rx="6" fill="url(#cg)"/><path d="M0 9h36M0 19h36M12 0v28M24 0v28" stroke="#92400e" stroke-opacity=".6" fill="none"/><rect x="12" y="9" width="12" height="10" rx="3" fill="url(#cg)" stroke="#92400e" stroke-opacity=".7"/></g>
<text x="134" y="334" font-size="8" letter-spacing="2" fill="#6b7190" class="m">ACCESS</text><text x="134" y="348" font-size="11" font-weight="700" fill="#e6e8f2">ALL REPOS</text>
<g fill="#e6e8f2" fill-opacity=".9">{barcode}</g>
<g clip-path="url(#bc)"><g transform="rotate(20 160 276)"><rect x="-30" y="100" width="60" height="400" fill="url(#hf)"><animate attributeName="x" values="-30;300;300" keyTimes="0;.55;1" dur="5s" repeatCount="indefinite"/></rect></g></g></g>
</g></g>
</g>
<rect x="1" y="1" width="898" height="418" rx="21" fill="none" stroke="url(#ab)" stroke-width="1.5"/></g>

<g transform="translate(340,0)">
<text x="24" y="36" font-size="11" letter-spacing="3" fill="#22d3ee" class="m">// DASHBOARD</text>
{tiles}
<rect x="24" y="146" width="236" height="230" rx="14" fill="#14162a" stroke="url(#ab)" stroke-opacity=".6"/>
<text x="40" y="176" font-size="11" letter-spacing="3" fill="#22d3ee" class="m">// TECH USED</text>
{bars_svg}{hint}
<rect x="272" y="146" width="264" height="230" rx="14" fill="#14162a" stroke="url(#ab)" stroke-opacity=".6"/>
<circle cx="292" cy="171" r="4" fill="#34d399"><animate attributeName="opacity" values="1;.3;1" dur="1.6s" repeatCount="indefinite"/></circle>
<text x="304" y="176" font-size="11" letter-spacing="3" font-weight="700" fill="#f472b6" class="m">// NOW</text>
{now_svg}
<text x="24" y="402" font-size="9" letter-spacing="2" fill="#6b7190" class="m">@RAJNISHMISHRA10 · AUTO-UPDATES EVERY 6H</text>
</g>
</svg>'''
open(OUT, "w", encoding="utf-8").write(svg)
print("wrote", OUT, len(svg), "bytes")
