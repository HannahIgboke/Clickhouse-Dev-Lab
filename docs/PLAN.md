# ClickHouse Dev Lab — plan for review

_Status: proposal. Nothing here is built yet. Read, mark what you agree with, answer the
open questions at the end, and we start._

---

## 1. Executive summary

You set out to "flesh out ideas before building". In fact the core product is already built:
a real ClickHouse server, a real `clickhouse-client`, 36 auto-graded tasks covering every
official objective, a grader that inspects the database rather than your keystrokes, timed
mock exams, and a self-test harness that proves every task's solution works.

So the two things genuinely left are:

1. **Depth.** Close the remaining content gaps so drill practice is as hard as the real exam.
2. **The idea you raised at the end — deployment.** Today the tool only runs locally
   (Docker + Python). You want *"click a link and it's a CLI in the browser."* That is a new
   layer on top of an existing, well-factored core. Section 6 lays out four ways to do it and
   recommends a two-phase path: **Codespaces first (days, $0), then a Fly.io "ephemeral
   container per session" product.**

The single most important design fact from the two links: **the exam is graded on outcomes,
in `clickhouse-client`, with the docs open.** Your grader already matches that philosophy —
it is the moat, and it is why the hosted version must keep the *real* client, not a browser
SQL box.

---

## 2. Ground truth from the pages you shared

From <https://clickhouse.com/learn/certification> (the authoritative source; the training page
behind `learn.clickhouse.com` is account-gated — it returned HTTP 403 to me):

| Fact | Value |
| --- | --- |
| Format | 100% hands-on, performance-based, real-world tasks |
| Tool | `clickhouse-client` |
| Deliverable | 10–12 tasks |
| Time | 2 hours |
| Price | US$200 per attempt (non-refundable), valid 365 days |
| Vendor | HackerRank (environment + task UI), proctored/supervised |
| Docs | ClickHouse documentation is available during the exam |
| Prerequisite | None, but the **Real-time Analytics with ClickHouse** course is recommended and "covers all the exam objectives" |
| Result | Email within 5 business days; digital badge via Credly |
| Sandbox | A ClickHouse *service* you create/operate (not a fixed toy schema) |

### The official objectives (verbatim grouping)

**Modeling data** — create a database; create a table to given criteria / matching a file
format; choose efficient data types; define an efficient primary key for the queries that will
run on a MergeTree table; define and query a Dictionary.

**Inserting data** — insert a local file; insert a file from cloud storage; insert Parquet, CSV
or TSV; provide minor transformations while inserting; insert from one table into another.

**Analyzing data** — write a query to given criteria; use regular functions (substring search,
timestamp → start of interval); use aggregate functions (max/min/sum/avg, uniques, quantile);
use GROUP BY to bucket aggregates over a timeframe/grouping.

**Optimizing query performance** — materialized view storing a non-aggregation result;
materialized view storing an aggregate via AggregatingMergeTree/SummingMergeTree; a projection;
a set or minmax skipping index.

**Deduplication and mutations** — a lightweight delete; an upsert strategy with
ReplacingMergeTree; frequent updates with CollapsingMergeTree.

**What this implies for the product**

- Practice must be **CLI-first**. A web SQL console trains the wrong muscle memory.
- Practice must be **timed and docs-open**, or it will over-prepare in the wrong direction.
- The score must reflect **what is in the server** (schema, engine, key, data, behaviour) —
  exactly what your grader does. Free-text "explain your reasoning" is not part of the exam.
- An "efficient primary key" and "efficient data types" are *judgement* marks, which is why
  `EXPLAIN indexes = 1` granule checks and type-regex checks are the right grading tools.

---

## 3. What you already have (audit)

| Layer | Files | State |
| --- | --- | --- |
| CLI | `chlab/cli.py` (~760 LOC) | `up/down/list/start/client/check/solution/reset/exam/sprint/speed/status/brief/submit/abandon/history/report/lint/selftest/site` |
| Grader | `chlab/grader.py` (~250 LOC) | 5 check types: `sql_true`, `column_types`, `granules` (via `EXPLAIN indexes = 1`), `explain_contains`, `result` (with tolerance; can re-run a user's own view on unmerged data) |
| Server I/O | `chlab/ch.py` | HTTP for setup/grading; real `clickhouse-client` for solutions; S3 stand-in (moto) |
| Tasks | `tasks/*.yaml` × 36 | Each carries brief, setup, checks with points+partial credit, hints, a reference solution, alternatives, and known-wrong solutions |
| Exams | `exams.yaml` | 3 fixed sets of 11 tasks + random generator enforcing tier/domain shape |
| Site | `chlab/site.py` | Static catalogue + setup guide for GitHub Pages |
| Infra | `docker-compose.yml` | `clickhouse-server:25.8` + `moto` S3, localhost-bound |
| CI/dev | `.github/workflows/*`, `.devcontainer/devcontainer.json` | selftest on PR; Pages publish; Codespaces with docker-in-docker |

Notable strengths to protect:

- **Grading by outcome, not by typo-matching.** Any correct approach scores 100%. This is rare
  and is the reason the tool is useful.
- **`chlab selftest`** proves references *and* alternatives score 100% and wrong solutions fail
  the right checks. Keep this gate on every content change.
- **`CHLAB_CLIENT` override already exists** in `ch.client_command()`. That one env var is what
  makes the hosted refactor cheap (see §7).

---

## 4. Coverage vs the 21 objectives

Every objective has at least one task; several have many. Counts:

| Objective | Tasks | Depth note |
| --- | --- | --- |
| M1 database | 1, 4, 12 | fine |
| M2 table to criteria/format | 1, 4, 12, 15, 16, 23, 29, 31, 34 | strong |
| M3 efficient types | 1, 8, 10, 12, 34 | strong |
| M4 primary key | 1, 12, 15, 30 | strong |
| M5 dictionary | 13, 14, 29 | good; layouts only hashed/range |
| I1 local file | 1, 5, 10, 12 | good |
| I2 cloud storage | 8, 9, 29 | S3 only |
| I3 Parquet/CSV/TSV | 1, 5, 8, 9, 10, 12, 29 | strong |
| I4 transform on insert | 9, 10, 11, 24, 29, 35 | strong |
| I5 table → table | 3, 11, 15, 16, 23, 24, 30, 31, 34 | strong |
| A1 query to criteria | many | strong |
| A2 regular functions | 2, 11, 26, 28, 35 | substring/date-fns could go deeper |
| A3 aggregates | many | strong |
| A4 GROUP BY buckets | 2, 14, 17, 18, 25, 29, 30 | `WITH FILL`/rollup not covered |
| O1 MV (non-agg) | 16, 35 | good |
| O2 MV (agg) | 17, 18, 29 | good |
| O3 projection | 19, 36 | good |
| O4 skipping index | 20, 21 | only `set`/`minmax` (as specified) |
| D1 lightweight delete | 7, 30 | could be deeper |
| D2 ReplacingMergeTree | 3, 24, 30 | strong |
| D3 CollapsingMergeTree | 22, 23 | strong |
| S1–S4 stretch | 31–34 | bonus material |

**Verdict: coverage is complete.** The remaining work is *depth and variety within* each
objective, not filling holes.

---

## 5. Content gaps worth closing (prioritised)

Priority 1 — things the real exam is likely to throw that you don't yet drill:

1. **More formats for I3.** Add `Values`, `JSONEachRow` with nested/array payloads,
   `Parquet` *writing* and re-reading, `Native`, `ORC`/`Avro`, and **gzip/zstd-compressed CSV**
   read via `FROM INFILE ... COMPRESSION` / `file()` / `s3()`.
2. **Cloud storage variants for I2.** `s3()` vs `INSERT ... SELECT FROM s3(...)` vs
   `INSERT INTO ... FROM INFILE`; a **glob** over many files with `_path` extraction;
   reading by explicit schema vs inference; and a *docs-only* GCS/Azure variant (no local
   emulator needed — the skill is knowing the syntax).
3. **A2/A4 depth.** `toStartOfInterval`/`toStartOfFifteenMinutes`, `formatDateTime`,
   `substring`/`position`/`extract`, `JSONExtract*`, `replaceRegexpAll`, quantiles
   (`quantile`, `quantiles`, `median`), `uniq` vs `uniqExact`, `countIf`, and
   `GROUP BY ... WITH ROLLUP/CUBE/TOTALS` and `WITH FILL STEP INTERVAL`.
4. **D1 depth.** A lightweight `DELETE ... WHERE` that must respect partitions, contrasted
   with a heavy `ALTER ... DELETE` mutation, and the "erase then re-aggregate" workflow.
5. **Dictionary depth (M5).** `complex_key_hashed`, `range_hashed` with explicit bounds,
   `INJECTIVE`, and querying via `dictGet`/`dictGetOrDefault` — plus a dictionary over a
   ClickHouse table vs a local file.
6. **Settings and correctness traps.** `FINAL`, `OPTIMIZE ... FINAL`, `optimize_on_insert`,
   `apply_deleted_mask`, `date_time_input_format`, `input_format_*`, `allow_experimental_*`.
   These are where candidates silently produce wrong answers.

Priority 2:

7. **Scale realism.** Some briefs use ~0.5M rows; the real service may hold more. Add one or
   two "sizeable but quick to seed" datasets so `EXPLAIN`/timing feel real without a 2 GB
   download (generate deterministically from `numbers()`/`generateRandom`, as tasks already do).
8. **Reading a spec you didn't write.** Add tasks where the requirement is only in a file
   (e.g. `/data/SPEC.md` or a JSON schema) to mirror "satisfies a given criteria".
9. **Window functions** (not an objective, but adjacent and increasingly common) — stretch tier.
10. **More wrong-solution coverage.** The faster a learner's wrong answer is caught by a
    named check, the better the teaching. Aim for ≥2 known-wrong solutions per objective task.

Priority 3 (product, not content):

11. **Post-attempt explanation.** After `chlab check`, offer a short "why this matters" note per
    failed check (you already have `hint`; add a longer `why`).
12. **Objective-level readiness** already exists (`chlab report`) — later, add a "predicted exam
    score" with a confidence band from mock-exam history.

---

## 6. The deployment decision (your main new question)

Goal restated: *a link a person clicks, which drops them into a working `clickhouse-client`
like the exam.*

There are four viable shapes. The trade-off is always **fidelity of the CLI** vs **isolation
of the session** vs **cost and ops burden**.

| | **A. Local (today)** | **B. Shared server, browser terminal** | **C. Ephemeral container per session** | **D. In-browser WASM** |
| --- | --- | --- | --- | --- |
| What the user does | clone → install → `chlab up` | click link → browser terminal | click link → browser terminal | click link → fake terminal in the page |
| Real `clickhouse-client`? | Yes | Yes | Yes | No (WASM `clickhouse-local`, or a SQL box) |
| `FROM INFILE /data/...`? | Yes | Yes (per-session dir) | Yes | Different semantics |
| Isolation between users | N/A (own machine) | Weak — shared server, shared `system.*`, resource contention | Strong — own server, own disk | Perfect (nothing server-side) |
| Closest to the exam | Yes, but setup friction | Close | Closest, and disposable | Least |
| Infra to run | none | 1 ClickHouse + a web terminal + auth | orchestration (Fly Machines / containers) + auth | static hosting only |
| Cost to you | $0 | low | medium (per session-hour) | ~$0 |
| Effort to ship | done | moderate | high | medium (and fidelity is poor) |
| Main risk | "it doesn't just work" | one user can hurt others; tenant escaping via `system`; a runaway query OOMs everyone | cost/abuse; orchestration bugs | trains wrong habits; can't reuse your server-side grader |

**Recommendation: two phases.**

### Phase 1 — "click a link" in days, at $0 (Option A + Codespaces)

- Push the repo to GitHub. You already have `.devcontainer/devcontainer.json` with
  docker-in-docker and `postStartCommand: chlab up`, and `pages.yml` publishing the catalogue.
- Wire the Pages site's hero button to **"Open in Codespaces"**
  (`https://codespaces.new/<owner>/clickhouse-dev-lab`). One click → a real Linux box → `chlab up`
  already running → terminal ready.
- Cost model is ideal: Codespaces bills the **user's** free monthly core-hours, not yours.
- Add a "Run locally" button for people who prefer Docker.
- Add a 60-second screencast/GIF on the page so the click is obviously worth it.

This gets you a shareable link this week and validates demand before you build servers.

### Phase 2 — the product-grade "real CLI in the browser" (Option C)

Only build this once Phase 1 shows people actually use it. Reference architecture:

```
Browser
  ├─ static site (extend chlab/site.py)  → landing page, task catalogue, results
  ├─ xterm.js terminal        ← WebSocket (ttyd) ─┐
  └─ "Start exam" button → POST /api/session      │
                                                  │
Session service (FastAPI or Node; small VPS or Fly)│
  ├─ auth: GitHub OAuth or magic link             │
  ├─ rate limit: 1 live session/user, N/IP, CAPTCHA on start
  ├─ orchestration: Fly Machines API (or docker run on a VPS)
  │     → boots image  chlab-session  and returns its url
  ├─ reaper: stop machines idle > 10 min, hard cap 2 h
  └─ state: Postgres/SQLite (session → user → task → scores)

chlab-session image (one per user, disposable)
  ├─ clickhouse-server (25.8 LTS)         ← own disk, own DB namespace
  ├─ clickhouse-client                    ← what the user types into
  ├─ clickhouse-dev-lab (chlab)               ← `chlab check`, `chlab exam`, grader
  ├─ ttyd  → serves clickhouse-client over WebSocket
  └─ /data  → this session's generated task files
```

Key points:

- **The terminal is a real PTY.** `ttyd` (a small C binary) exposes any command — here
  `clickhouse-client` — over WebSocket; `xterm.js` renders it in the page. That is the standard
  way to put a genuine CLI in a browser. (`wetty` is the Node alternative.)
- **Isolation is per session, not per user database.** Your grader creates a `chlab_grader`
  database and tasks do `DROP DATABASE ... SYNC`; on a shared server those collide across users
  and a careless `SYSTEM`/`KILL` can touch other tenants. A disposable container removes the
  whole class of problem. This alone justifies Option C over B.
- **Your code is already deploy-friendly.** `ch.client_command()` honours `CHLAB_CLIENT` and
  `CHLAB_HTTP`; inside the session set `CHLAB_CLIENT="clickhouse-client"`,
  `CHLAB_HTTP="http://localhost:8123"`, and everything works with no source change. The
  docker-compose `clickhouse` service can be reused verbatim inside the image.
- **Where the grader runs.** Keep it server-side, inside the session: the "Grade me" button
  calls a tiny local endpoint (or just has the user run `chlab check` in the terminal, which is
  more exam-like). Do **not** move grading to the browser.
- **Persist progress** by having the session POST results to the control plane before it dies,
  so `chlab report` continuity survives across sessions (an account is then required).

What you'd add to the repo:

| New thing | Purpose |
| --- | --- |
| `chlab/serve.py` (or a small `web/` app) | session API: create/stop/list, auth, limits |
| `deploy/session.Dockerfile` | ClickHouse + client + chlab + ttyd, with an init that seeds `/data` |
| `deploy/fly.toml` (or `compose.session.yml`) | orchestration recipe |
| `web/` (xterm.js + landing) | the actual browser page; reuses `site.py` CSS |
| `chlab export-state` / `chlab import-state` | move scores between local and hosted |
| CI job | build + smoke-test the session image on every push |

### Why not the other two

- **Option B (shared server + per-user ClickHouse user/grants)** is the cheapest per concurrent
  user, but ClickHouse's single-tenant-per-server assumptions leak (`system.*`, query memory,
  merges) and one abusive query degrades everyone. Keep it only as an emergency cost valve.
- **Option D (WASM `clickhouse-local` in the browser)** — ClickHouse does ship a WebAssembly
  build (the docs/sql playground uses it) and it needs no server, but it is *not*
  `clickhouse-client`, `FROM INFILE` semantics differ, and you cannot reuse your
  server-side grader. For an exam-fidelity product that is a step backwards, though it would be
  a fine free "try it without signing up" teaser.

### There is also an off-the-shelf middle path (Option E)

Before writing any orchestration, consider hosting the labs as **Killercoda**-style scenarios
(in-browser Ubuntu VM with a verify script) or as a **Gitpod/DevPod** devcontainer. These give
"click → terminal" with almost no build. Downsides: less branding control, per-session limits,
and you rely on someone else's free tier. Worth a day's spike as an alternative to Phase 2.

---

## 7. Concrete repo changes for hosting

Small, because the core is well-factored:

1. **Path/config abstraction.** Tasks currently write files to `workspace/data` and mount them
   read-only. Add `CHLAB_DATA_DIR` and `CHLAB_STATE_DIR` so a session uses its own temp dirs.
2. **`CHLAB_CLIENT` / `CHLAB_HTTP`.** Already present; document the hosted values.
3. **Grader hygiene on shared servers.** Even if you go per-container, make `chlab_grader` unique
   per session (`chlab_grader_<id>`) so B is safe if you ever need it.
4. **`chlab check --json`.** Emit machine-readable results so a web UI can render the score
   without scraping ANSI.
5. **Version pinning.** Confirm `clickhouse/clickhouse-server:25.8` is still a sensible LTS
   before freezing; the compose file says to bump deliberately and re-run `chlab selftest`.
6. **Session image smoke test** in CI: boot the image, run `chlab selftest --timing` for a couple
   of tasks, assert exit 0.
7. **Abuse controls** in the session service: one live session per user, global concurrency cap,
   spend alert, CAPTCHA/email verification at start, and a hard 2 h kill (matching the exam).

---

## 8. Cost, abuse and legal (rough)

- **Phase 1:** $0 to you (Codespaces bills the user).
- **Phase 2:** cost ≈ (concurrent sessions) × (session length) × (machine price). A 1 vCPU /
  2 GB machine is enough for the current task sizes. Example shape to validate with current
  prices: 20 concurrent testers × 45 min/day ≈ 15 machine-hours/day; a single mid-size VPS that
  runs ~10 containers beats per-session cloud VMs until you outgrow it. **Treat all pricing as
  "verify today" — it changes.**
- **Abuse is the real risk**, not steady cost: crypto-mining inside ClickHouse (`URL`/S3 egress),
  looping queries, or simply leaving sessions open. Mitigate with idle-stop, hard caps, an
  outbound-network allowlist on the session image, and per-IP rate limits.
- **Legal:** keep the "unofficial, not affiliated with ClickHouse, Inc." disclaimer everywhere
  (you already do). Never accept or publish real exam questions. Attribute ClickHouse docs.
  Consider an explicit no-warranty + acceptable-use note once you host other people's sessions.

---

## 9. Suggested roadmap

| Phase | Deliverable | Rough effort |
| --- | --- | --- |
| 0 | Push repo to GitHub; enable Pages; add "Open in Codespaces" button + demo GIF | hours |
| 1 | Content: close Priority-1 gaps (§5.1–6) with `chlab selftest` green | days |
| 2 | `chlab check --json`, `CHLAB_DATA_DIR`/`CHLAB_STATE_DIR`, per-session grader DB | ~1 day |
| 3 | Spike: session image (`ch + client + chlab + ttyd`) running locally via Docker | ~1 day |
| 4 | Control plane: auth, session API, reaper, progress persistence | days |
| 5 | Landing page with xterm.js; wire "Start exam" → session | days |
| 6 | Cost/perf tuning, abuse controls, beta with a handful of testers | ongoing |

---

## 10. Open questions for you (please answer before we build)

1. **Goal.** Is this a personal portfolio / community freebie, or a commercial product?
   (Drives Phase 2 and how much abuse-hardening matters.)
2. **Fidelity.** Must it be the *real* `clickhouse-client` in a real container, or is a browser
   SQL console acceptable? My strong recommendation is the real client — say so if you disagree.
3. **Infra appetite & budget.** Are you willing to run a VPS or a Fly.io account and pay a small
   monthly amount? A hard ceiling?
4. **Accounts.** Do you need cross-device progress and a "certificate", or are anonymous
   sessions fine? (Accounts make the reaper and persistence much simpler.)
5. **Branding.** Keep the name ClickHouse Dev Lab? Buy a domain? Vanilla-JS site or a small
   framework?
6. **Content scope before launch.** Ship the existing 36 (plus gap-fill), or hold for, say, 50+
   tasks?
7. **Timeline.** When is your exam? That decides whether we do Phase 0–1 now and Phase 2 after
   you have passed, or sprint at the whole thing.

---

## Appendix A — how grading works today (so we don't regress it)

`chlab/grader.py` runs, per check:

- `sql_true` — a boolean query against `system.*` (existence, engine, key order).
- `column_types` — regex per column, **partial credit per column**.
- `granules` — `EXPLAIN indexes = 1`, read/total granules ratio vs a target (the "efficient
  primary key" mark); `stage: final` measures after skip indexes/projections.
- `explain_contains` — the plan must mention e.g. a projection's name.
- `result` — compare rows to an independent `expect` query, with tolerance and optional column
  assertions; can re-run **the user's own view** against an *unmerged* copy of the data, so a
  materialized view can't hide behind merge timing.

Checks may carry `prepare`/`cleanup` SQL. Every task ships a reference solution, alternatives
and known-wrong solutions; `chlab selftest` asserts references/alternatives score 100% and each
wrong solution fails exactly the named checks. **Every hosted change must keep this green.**

## Appendix B — one thing to fix in your own study plan

Your brief said you studied via the Cloud SQL console. Since the exam is
`clickhouse-client`-only, switch your own practice *now* to `chlab client` for every task, use
only `clickhouse.com/docs` with no AI, and time yourself against each task's target. Do all
three fixed mock exams plus random ones; book the real exam only once you clear 80%+ twice in a
row. The tool you built is the right tool to train on — use it before you shape it further.
