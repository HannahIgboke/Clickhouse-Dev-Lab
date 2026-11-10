"""Builds the static website (GitHub Pages) from the task files. No dependencies."""

from __future__ import annotations

import html
import os
from pathlib import Path

import yaml

from . import __version__, ch
from . import objectives as OBJ
from . import tasks as T

REPO_SLUG = os.environ.get("GITHUB_REPOSITORY", "HannahIgboke/Clickhouse-Dev-Lab")
REPO_URL = "https://github.com/" + REPO_SLUG
# One click -> a real Linux box with ClickHouse and clickhouse-client already running.
# Codespaces bills the user's own free monthly hours, so hosting costs the project nothing.
CODESPACES_URL = "https://codespaces.new/" + REPO_SLUG + "?quickstart=1"

CSS = """
:root { --ink:#1d1b16; --muted:#6b6658; --line:#e4dfd3; --bg:#fbf9f4; --card:#ffffff;
        --accent:#c2410c; --accent-soft:#fdeee5; --good:#15803d; --code:#f3efe6; }
.cta { display:flex; flex-wrap:wrap; gap:12px; margin: 6px 0 4px; }
.cta a { display:inline-flex; align-items:center; gap:8px; text-decoration:none;
         padding: 12px 20px; border-radius: 10px; font-weight: 600; font-size: 15px;
         border: 1px solid var(--line); background: var(--card); color: var(--ink); }
.cta a.primary { background: var(--accent); border-color: var(--accent); color:#fff; }
.cta a:hover { filter: brightness(0.97); }
@media (prefers-color-scheme: dark) {
  :root { --ink:#ece8df; --muted:#a39d8f; --line:#38342c; --bg:#16140f; --card:#1f1c16;
          --accent:#fb923c; --accent-soft:#3a2416; --good:#4ade80; --code:#2a261e; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font: 16px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 48px 24px 96px; }
h1 { font-size: 44px; line-height:1.1; margin: 0 0 12px; letter-spacing:-0.02em; }
h1 span { color: var(--accent); }
h2 { font-size: 24px; margin: 56px 0 12px; letter-spacing:-0.01em; }
h3 { font-size: 18px; margin: 28px 0 8px; letter-spacing:-0.01em; }
p.lead { font-size: 19px; color: var(--muted); max-width: 680px; margin: 0 0 20px; }
.note { font-size: 14px; color: var(--muted); border-left: 3px solid var(--line); padding-left: 12px; }
code, pre { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 14px; }
code { background: var(--code); padding: 1px 5px; border-radius: 4px; }
pre { background: var(--code); padding: 16px; border-radius: 8px; overflow-x: auto; line-height: 1.5; }
pre code { background: none; padding: 0; }
a { color: var(--accent); }
.stats { display:flex; gap: 28px; flex-wrap: wrap; margin: 28px 0; }
.stats div { font-size: 14px; color: var(--muted); }
.stats b { display:block; font-size: 30px; color: var(--ink); }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-weight: 600; color: var(--muted); font-size: 13px; }
td.n { text-align: right; font-variant-numeric: tabular-nums; }
.pill { display:inline-block; font-size: 12px; padding: 1px 8px; border-radius: 999px;
        background: var(--accent-soft); color: var(--accent); margin: 0 4px 4px 0; white-space: nowrap; }
.tier { font-size: 12px; color: var(--muted); }
details.task { background: var(--card); border: 1px solid var(--line); border-radius: 10px; margin: 10px 0; }
details.task summary { cursor: pointer; padding: 14px 16px; list-style: none; display:flex; gap: 12px; align-items: baseline; }
details.task summary::-webkit-details-marker { display:none; }
details.task summary .id { color: var(--muted); font-variant-numeric: tabular-nums; min-width: 28px; }
details.task summary .title { font-weight: 600; flex: 1; }
details.task .body { padding: 0 16px 16px 56px; }
details.task pre { white-space: pre-wrap; font-size: 13.5px; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.box { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
.box h3 { margin: 0 0 6px; font-size: 16px; }
.box p { margin: 0; font-size: 14px; color: var(--muted); }
footer { margin-top: 72px; font-size: 13px; color: var(--muted); }
"""


def _e(s) -> str:
    return html.escape(str(s))


def build(out: Path) -> None:
    tasks = T.load_all()
    exam_tasks = [t for t in tasks if not t.stretch]
    exams_file = ch.REPO_ROOT / "exams.yaml"
    sets = yaml.safe_load(exams_file.read_text())["exams"] if exams_file.exists() else []
    by_id = {t.id: t for t in tasks}

    rows = []
    for code in OBJ.exam_codes() + [c for c in OBJ.OBJECTIVES if c.startswith("S")]:
        covering = [t for t in tasks if code in t.objectives]
        links = " ".join(f'<a href="#t{t.id}">{t.id}</a>' for t in covering)
        rows.append(f"<tr><td><b>{code}</b></td><td>{_e(OBJ.OBJECTIVES[code])}</td>"
                    f"<td>{_e(OBJ.DOMAINS[code[0]])}</td><td class='n'>{len(covering)}</td><td>{links}</td></tr>")

    cards = []
    for t in tasks:
        pills = "".join(f'<span class="pill" title="{_e(OBJ.OBJECTIVES.get(o, o))}">{o}</span>' for o in t.objectives)
        docs = "".join(f'<li><a href="{_e(d)}">{_e(d.replace("https://clickhouse.com/docs/", ""))}</a></li>' for d in t.docs)
        cards.append(f"""
<details class="task" id="t{t.id}">
  <summary><span class="id">{t.id}</span><span class="title">{_e(t.title)}</span>
    <span class="tier">Tier {t.tier} · {t.minutes} min · {t.points} pts</span></summary>
  <div class="body">
    <div>{pills}</div>
    <pre>{_e(T.fill(t.brief))}</pre>
    <p>Start it with <code>chlab start {t.id}</code>.</p>
    {"<p class='note'>Docs:</p><ul>" + docs + "</ul>" if docs else ""}
  </div>
</details>""")

    exam_rows = []
    for s in sets:
        ts = [by_id[i] for i in s["tasks"] if i in by_id]
        exam_rows.append(f"<tr><td><code>chlab exam --set {s['id']}</code></td><td class='n'>{len(ts)}</td>"
                         f"<td>{', '.join(str(t.id) for t in ts)}</td></tr>")

    tiers = {k: sum(1 for t in exam_tasks if t.tier == k) for k in (1, 2, 3, 4)}
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClickHouse Dev Lab · hands-on ClickHouse certification practice</title>
<meta name="description" content="Free, unofficial, terminal-first practice for the ClickHouse Certified Developer exam: real clickhouse-client, auto-graded tasks, mock exams.">
<style>{CSS}</style>
</head>
<body><main>
<h1>ClickHouse<span>DevLab</span></h1>
<p class="lead">Free, hands-on practice for the ClickHouse Certified Developer exam, in the same tool the exam uses:
<code>clickhouse-client</code>. Fresh data every attempt, a grader that checks your database and explains what is wrong,
and timed mock exams.</p>
<p class="note">Unofficial community project, not affiliated with or endorsed by ClickHouse, Inc. Tasks are written from the
<a href="https://clickhouse.com/learn/certification">published exam objectives</a> and public docs, never from real exam content.</p>

<div class="cta">
  <a class="primary" href="{CODESPACES_URL}">▶ Open in a browser (one click, free)</a>
  <a href="{REPO_URL}#setup-once">Run it locally with Docker</a>
</div>
<p class="note">The button opens a free GitHub Codespace: a real Linux machine with ClickHouse
25.8 and <code>clickhouse-client</code> already running, in your browser. It uses your own GitHub
free hours (about 60 hours/month on the default machine) &mdash; there is no server to pay for and
nothing to install. <b>Stop the Codespace when you finish</b> so you don't use up your hours.</p>

<div class="stats">
  <div><b>{len(tasks)}</b>auto-graded tasks</div>
  <div><b>{len(OBJ.exam_codes())}/{len(OBJ.exam_codes())}</b>exam objectives covered</div>
  <div><b>{len(sets)} + ∞</b>mock exams (fixed + random)</div>
  <div><b>$0</b>runs on your machine</div>
</div>

<h2>Get started</h2>
<div class="cta">
  <a class="primary" href="{CODESPACES_URL}">▶ Open in a browser (one click, free)</a>
</div>
<p>Click the button, wait about a minute for the machine to install everything and start ClickHouse
(<code>chlab up</code> runs by itself), then in the terminal:</p>
<pre><code>chlab list        # the tasks
chlab start 1     # fresh data + the brief
chlab client      # work here, exactly like the exam
chlab check       # grade yourself</code></pre>
<p class="note">On first use, GitHub may ask you to authorise Codespaces. Pick the smallest
machine (2 cores) &mdash; it is plenty. Stop the Codespace when you finish; the free allowance is
about 60 hours/month on that machine.</p>

<h3>Or run it on your own machine</h3>
<p>You need Docker and Python 3.9+. This costs nothing and needs no GitHub account.</p>
<pre><code>git clone {REPO_URL}.git
cd clickhouse-dev-lab
pip install -e .
chlab up          # ClickHouse 25.8 + a local S3 stand-in, in Docker
chlab list
chlab start 1
chlab client
chlab check</code></pre>

<h2>Ways to practise</h2>
<div class="grid">
  <div class="box"><h3>In the browser, one click</h3><p>Press <b>Open in a browser</b> above. A real Linux machine boots with ClickHouse running, using your free GitHub hours. Nothing to install, nothing to pay.</p></div>
  <div class="box"><h3>Drill</h3><p><code>chlab start &lt;n&gt;</code> then <code>chlab check</code> as often as you like. Hints on failure, solutions when you're done.</p></div>
  <div class="box"><h3>Mock exam</h3><p><code>chlab exam</code>: 11 tasks, 120 minutes, no checking or solutions until <code>chlab submit</code>. Weighted score against the 70% pass mark.</p></div>
  <div class="box"><h3>Domain sprint</h3><p><code>chlab sprint optimizing</code>: up to 5 tasks from one exam domain in 45 minutes.</p></div>
  <div class="box"><h3>Speed run</h3><p><code>chlab speed</code>: a random tier-1 task against a 5-minute clock, to build typing fluency.</p></div>
  <div class="box"><h3>Readiness report</h3><p><code>chlab report</code>: your score per objective and what to practise next.</p></div>
  <div class="box"><h3>How grading works</h3><p>The grader inspects tables, engines, keys, data and behaviour (it inserts test rows, runs EXPLAIN, re-runs your views on unmerged data). Any correct approach scores full marks.</p></div>
</div>

<h2>Objective coverage</h2>
<p>Exam-level tasks by tier: {tiers[1]} foundation, {tiers[2]} exam level, {tiers[3]} hard, {tiers[4]} nightmare. S-codes are stretch topics from the course that are not listed objectives.</p>
<table><thead><tr><th>Code</th><th>Objective</th><th>Domain</th><th class="n">Tasks</th><th>Task numbers</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>

<h2>Mock exams</h2>
<table><thead><tr><th>Command</th><th class="n">Tasks</th><th>Task numbers</th></tr></thead>
<tbody>{''.join(exam_rows)}<tr><td><code>chlab exam</code></td><td class="n">11</td><td>random, same shape</td></tr></tbody></table>

<h2>All tasks</h2>
{''.join(cards)}

<footer>ClickHouse Dev Lab {__version__} · MIT licensed · <a href="{REPO_URL}">source and contributions</a> ·
ClickHouse is a trademark of ClickHouse, Inc.</footer>
</main></body></html>
"""
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
