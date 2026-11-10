"""chlab: the ClickHouse Dev Lab command line."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

import yaml

from . import __version__, ch, grader
from . import objectives as OBJ
from . import tasks as T

STATE_FILE = ch.REPO_ROOT / ".chlab" / "state.json"
EXAMS_FILE = ch.REPO_ROOT / "exams.yaml"
EXAM_MINUTES = 120
SPRINT_MINUTES = 45
SPEED_MINUTES = 5

# ---------------------------------------------------------------- output ----

if os.name == "nt":
    os.system("")  # turn on ANSI colours in Windows terminals
_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _COLOR else s


def bold(s): return _c("1", s)
def dim(s): return _c("2", s)
def green(s): return _c("32", s)
def red(s): return _c("31", s)
def yellow(s): return _c("33", s)
def cyan(s): return _c("36", s)


def die(msg: str, code: int = 1):
    print(red("error: ") + msg, file=sys.stderr)
    sys.exit(code)


def mmss(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    return f"{h}:{rem // 60:02d}:{rem % 60:02d}" if h else f"{rem // 60}:{rem % 60:02d}"


def pct_color(p: float, text: str | None = None) -> str:
    text = text if text is not None else f"{p:.0f}%"
    return green(text) if p >= 70 else (yellow(text) if p >= 40 else red(text))


def bar(p: float, width: int = 20) -> str:
    filled = int(round(width * p / 100))
    return pct_color(p, "█" * filled) + dim("░" * (width - filled))

# ----------------------------------------------------------------- state ----


def load_state() -> dict:
    state = {"current": None, "session": None, "history": {}, "sessions": []}
    if STATE_FILE.exists():
        state.update(json.loads(STATE_FILE.read_text()))
    return state


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def require_server():
    if not ch.ping():
        die(f"ClickHouse is not reachable at {ch.HTTP_URL}. Start it with `chlab up`.")


def block_in_session(state: dict, what: str):
    s = state.get("session")
    if s:
        die(f"A {s['kind']} is in progress, so `chlab {what}` is not available "
            f"(just like the real exam). Use `chlab status`, `chlab brief <n>` and `chlab submit`, "
            f"or `chlab abandon` to end it without grading.")


def current_task(state: dict) -> T.Task:
    if not state.get("current"):
        die("No task in progress. Start one with `chlab start <id>` (see `chlab list`).")
    return T.find(str(state["current"]["id"]))


def record(state: dict, task: T.Task, pct: float, elapsed: float, mode: str):
    state["history"].setdefault(task.slug, []).append(
        {"score": round(pct, 1), "elapsed": round(elapsed), "mode": mode,
         "at": datetime.now().isoformat(timespec="seconds")})

# --------------------------------------------------------------- display ----


def print_brief(task: T.Task, heading: str | None = None):
    width = 78
    print(bold(cyan(heading or f"Task {task.id} · {task.title}")))
    meta = (f"{' + '.join(T.DOMAINS.get(d, d) for d in task.domains)} · Tier {task.tier} · "
            f"about {task.minutes} min · {task.points} points")
    print(dim(meta))
    print()
    for para in T.fill(task.brief).split("\n\n"):
        lines = para.splitlines()
        if any(l.startswith(("  ", "-", "|", "*")) for l in lines):
            print(para)
        else:
            print(textwrap.fill(" ".join(para.split()), width))
        print()


def print_docs(task: T.Task):
    if task.docs:
        print(dim("Docs that may help:"))
        for d in task.docs:
            print(dim(f"  {d}"))
        print()


def print_results(task: T.Task, results, elapsed: float | None, target_min: int | None = None,
                  failures_only: bool = False):
    earned, total = grader.score(results)
    pct = 100 * earned / total if total else 0
    verdict = green("PASS") if pct >= grader.PASS_MARK * 100 else red("BELOW PASS MARK")
    print(bold(f"Task {task.id} · {task.title}"))
    for r in results:
        if failures_only and r.passed:
            continue
        mark = green("✔") if r.passed else (yellow("◐") if r.earned > 0 else red("✘"))
        pts = f"{r.earned:g}/{r.points}"
        print(f" {mark} {pts:>6}  {r.name}")
        if not r.passed:
            if r.detail:
                print(textwrap.indent(textwrap.fill(r.detail, 68), " " * 11))
            if r.hint:
                print(dim(textwrap.indent(textwrap.fill("Hint: " + r.hint, 68), " " * 11)))
    if not failures_only:
        print()
        line = f"Score: {earned:g}/{total} ({pct:.0f}%) · {verdict} (exam pass mark is 70%)"
        if elapsed is not None:
            line += f" · time {mmss(elapsed)} (target {target_min or task.minutes}:00)"
        print(bold(line))
    return pct

# ------------------------------------------------------- basic commands ----


def cmd_up(args):
    print("Starting ClickHouse and the S3 stand-in (first run downloads the images)...")
    r = subprocess.run(["docker", "compose", "-f", str(ch.COMPOSE_FILE), "up", "-d"])
    if r.returncode != 0:
        die("docker compose failed. Is Docker running?")
    for _ in range(90):
        if ch.ping():
            try:
                ch.ensure_bucket()
            except ConnectionError:
                time.sleep(1)
                continue
            v = ch.scalar("SELECT version()")
            print(green("Ready") + f": ClickHouse {v}. Next: `chlab list`.")
            return
        time.sleep(1)
    die("ClickHouse did not answer within 90 seconds. Check `docker compose logs`.")


def cmd_down(args):
    subprocess.run(["docker", "compose", "-f", str(ch.COMPOSE_FILE), "down"])


def cmd_list(args):
    state = load_state()
    tasks = T.load_all()
    print(bold(f"{'#':>3}  {'Task':<22} {'Objectives':<22} {'Tier':<5} {'Min':>4}  {'Best':>5}"))
    for t in tasks:
        if t.stretch and not args.all:
            continue
        hist = state["history"].get(t.slug, [])
        best = max((h["score"] for h in hist), default=None)
        best_s = dim(f"{'-':>5}") if best is None else pct_color(best, f"{best:>4.0f}%")
        objs = ",".join(t.objectives)
        objs = objs if len(objs) <= 22 else objs[:21] + "…"
        print(f"{t.id:>3}  {t.slug:<22} {objs:<22} {t.tier:<5} {t.minutes:>4}  {best_s}")
    n_stretch = sum(t.stretch for t in tasks)
    if n_stretch and not args.all:
        print(dim(f"\n+ {n_stretch} stretch tasks beyond the exam objectives: `chlab list --all`."))
    print(dim("Start one with `chlab start <#>`. Objective codes: `chlab report`."))


def _start_single(task: T.Task, mode: str, target: int | None = None):
    state = load_state()
    block_in_session(state, "start")
    require_server()
    seed = random.randint(1, 1_000_000)
    print(dim(f"Preparing task {task.id} (fresh data)..."))
    try:
        T.prepare(task, seed)
    except ch.ClickHouseError as e:
        die("setup failed: " + grader.short_error(str(e)))
    state["current"] = {"id": task.id, "slug": task.slug, "seed": seed, "mode": mode,
                        "target": target or task.minutes, "started_at": time.time()}
    save_state(state)
    print()
    print_brief(task)
    print_docs(task)
    if mode == "speed":
        print(bold(yellow(f"Speed run: beat {target}:00. The clock is running.")))
    print(dim("Work in the client: `chlab client`. Grade yourself: `chlab check`."))


def cmd_start(args):
    _start_single(T.find(args.task), "practice")


def cmd_speed(args):
    pool = [t for t in T.load_all() if t.tier == 1]
    if not pool:
        die("No tier 1 tasks available.")
    _start_single(random.choice(pool), "speed", SPEED_MINUTES)


def cmd_client(args):
    cmd = ch.client_command(interactive=True) + args.extra
    try:
        sys.exit(subprocess.call(cmd))
    except FileNotFoundError:
        die(f"Could not run {cmd[0]!r}. Is Docker installed, or is CHLAB_CLIENT set correctly?")


def cmd_check(args):
    state = load_state()
    block_in_session(state, "check")
    require_server()
    task = current_task(state)
    cur = state["current"]
    elapsed = time.time() - cur["started_at"]
    results = grader.grade(task)
    pct = print_results(task, results, elapsed, cur.get("target"))
    record(state, task, pct, elapsed, cur.get("mode", "practice"))
    save_state(state)
    if pct < 100:
        print(dim("Fix what failed and run `chlab check` again, or see "
                  f"`chlab solution {task.id}` when you are done trying."))


def cmd_solution(args):
    state = load_state()
    block_in_session(state, "solution")
    task = T.find(args.task)
    print(bold(f"Reference solution · task {task.id} · {task.title}"))
    print(dim("Other correct approaches also score full marks; the grader checks results, not text.\n"))
    print(T.fill(task.solution))


def cmd_reset(args):
    require_server()
    state = load_state()
    targets = T.load_all() if args.task == "all" else [T.find(args.task)]
    for task in targets:
        T.reset(task)
    if args.task == "all":
        state["current"] = None
        state["session"] = None
    elif state.get("current") and state["current"]["id"] == targets[0].id:
        state["current"] = None
    save_state(state)
    print(f"Dropped objects for {len(targets)} task(s).")

# --------------------------------------------------- exams and sprints ----


def _tasks_by_id() -> dict[int, T.Task]:
    return {t.id: t for t in T.load_all()}


def _covers(tasks: list[T.Task]) -> set[str]:
    return {o[0] for t in tasks for o in t.objectives}


def pick_exam(rng: random.Random) -> list[T.Task]:
    """10–12 tasks like the real exam: 2 tier-1, 6 tier-2, 3 harder, all five domains."""
    pool = [t for t in T.load_all() if not t.stretch]
    by_tier = {k: [t for t in pool if t.tier == k] for k in (1, 2, 3, 4)}
    hard = by_tier[3] + by_tier[4]
    best = None
    for _ in range(500):
        pick = (rng.sample(by_tier[1], min(2, len(by_tier[1])))
                + rng.sample(by_tier[2], min(6, len(by_tier[2])))
                + rng.sample(hard, min(3, len(hard))))
        if _covers(pick) >= set("MIAOD"):
            best = pick
            break
        best = best or pick
    return sorted(best, key=lambda t: (t.tier, t.id))


def _start_session(kind: str, name: str, tasks: list[T.Task], minutes: int):
    state = load_state()
    if state.get("session"):
        die(f"A {state['session']['kind']} is already in progress. `chlab submit` or `chlab abandon` it first.")
    require_server()
    print(dim(f"Preparing {len(tasks)} tasks with fresh data. This can take a minute..."))
    seed_base = random.randint(1, 1_000_000)
    for i, t in enumerate(tasks, 1):
        try:
            T.prepare(t, seed_base + i)
        except ch.ClickHouseError as e:
            die(f"setup of task {t.id} failed: " + grader.short_error(str(e)))
    state["current"] = None
    state["session"] = {"kind": kind, "name": name, "tasks": [t.id for t in tasks],
                        "minutes": minutes, "started_at": time.time()}
    save_state(state)
    print()
    print(bold(cyan(f"{name} started: {len(tasks)} tasks, {minutes} minutes.")))
    print("Rules: docs only (clickhouse.com), no `chlab check` until you submit, no solutions.")
    print()
    cmd_status(None)
    print()
    print(dim("Read a task with `chlab brief <n>`, work in `chlab client`, and finish with `chlab submit`."))


def cmd_exam(args):
    rng = random.Random()
    if args.set:
        sets = yaml.safe_load(EXAMS_FILE.read_text())["exams"]
        chosen = next((s for s in sets if str(s["id"]) == str(args.set)), None)
        if not chosen:
            die(f"No mock exam set {args.set}. Sets: {', '.join(str(s['id']) for s in sets)}.")
        by_id = _tasks_by_id()
        tasks = [by_id[i] for i in chosen["tasks"]]
        name = f"Mock exam {chosen['id']}"
    else:
        tasks = pick_exam(rng)
        name = "Mock exam (random)"
    _start_session("mock exam", name, tasks, EXAM_MINUTES)


def cmd_sprint(args):
    key = args.domain.lower()
    letter = OBJ.DOMAIN_KEYS.get(key, key[:1].upper())
    if letter not in "MIAOD":
        die("Domain must be one of: modeling, inserting, analyzing, optimizing, dedup.")
    pool = [t for t in T.load_all() if not t.stretch and any(o[0] == letter for o in t.objectives)]
    rng = random.Random()
    rng.shuffle(pool)
    # prefer exam-level difficulty: a mix of tiers, at most 5 tasks
    pool.sort(key=lambda t: abs(t.tier - 2.4))
    tasks = sorted(pool[:5], key=lambda t: (t.tier, t.id))
    _start_session("sprint", f"{OBJ.DOMAINS[letter]} sprint", tasks, SPRINT_MINUTES)


def cmd_status(args):
    state = load_state()
    s = state.get("session")
    if not s:
        cur = state.get("current")
        if not cur:
            print("Nothing in progress. Try `chlab list`, `chlab exam` or `chlab sprint <domain>`.")
            return
        task = T.find(str(cur["id"]))
        el = time.time() - cur["started_at"]
        print(f"Task {task.id} · {task.title} · {cur.get('mode', 'practice')} · "
              f"elapsed {mmss(el)} of {cur.get('target', task.minutes)}:00")
        return
    by_id = _tasks_by_id()
    left = s["minutes"] * 60 - (time.time() - s["started_at"])
    clock = green(mmss(left)) if left > 900 else (yellow(mmss(left)) if left > 0 else red("TIME UP"))
    print(bold(f"{s['name']} · time left {clock}"))
    for n, tid in enumerate(s["tasks"], 1):
        t = by_id[tid]
        print(f"  {n:>2}. {t.title:<46} {dim(f'tier {t.tier} · ~{t.minutes} min · {t.points} pts')}")


def cmd_brief(args):
    state = load_state()
    s = state.get("session")
    if s:
        if args.n is None:
            cmd_status(None)
            return
        if not 1 <= args.n <= len(s["tasks"]):
            die(f"Pick a task number from 1 to {len(s['tasks'])}.")
        task = T.find(str(s["tasks"][args.n - 1]))
        print_brief(task, heading=f"{s['name']} · task {args.n} of {len(s['tasks'])} · {task.title}")
        left = s["minutes"] * 60 - (time.time() - s["started_at"])
        print(dim(f"Time left: {mmss(left)}."))
        return
    task = current_task(state)
    print_brief(task)
    print_docs(task)
    elapsed = time.time() - state["current"]["started_at"]
    print(dim(f"Elapsed: {mmss(elapsed)} of about {state['current'].get('target', task.minutes)}:00."))


def cmd_submit(args):
    state = load_state()
    s = state.get("session")
    if not s:
        die("No mock exam or sprint in progress. For a single task use `chlab check`.")
    require_server()
    elapsed = time.time() - s["started_at"]
    by_id = _tasks_by_id()
    rows = []
    print(dim("Grading..."))
    print()
    for n, tid in enumerate(s["tasks"], 1):
        task = by_id[tid]
        results = grader.grade(task)
        earned, total = grader.score(results)
        pct = 100 * earned / total if total else 0
        rows.append((n, task, pct, results))
        record(state, task, pct, elapsed, s["kind"])
    weight = sum(t.minutes for _, t, _, _ in rows)
    overall = sum(p * t.minutes for _, t, p, _ in rows) / weight if weight else 0
    passed = overall >= grader.PASS_MARK * 100

    print(bold(f"{s['name']} · results"))
    for n, task, pct, _ in rows:
        print(f"  {n:>2}. {task.title:<46} {pct_color(pct, f'{pct:>4.0f}%')}  {dim(f'weight {task.minutes}')}")
    print()
    by_domain: dict[str, list[float]] = {}
    for _, task, pct, _ in rows:
        for letter in sorted({o[0] for o in task.objectives}):
            by_domain.setdefault(letter, []).append(pct)
    for letter, ps in by_domain.items():
        avg = sum(ps) / len(ps)
        print(f"  {OBJ.DOMAINS[letter]:<30} {bar(avg)} {pct_color(avg)}")
    print()
    over = elapsed - s["minutes"] * 60
    time_note = f"time used {mmss(elapsed)} of {s['minutes']}:00"
    if over > 0:
        time_note += red(f" (over by {mmss(over)}; the real exam would have stopped you)")
    verdict = green(bold("PASS")) if passed else red(bold("NOT YET"))
    print(bold(f"Weighted score: {overall:.0f}% · {verdict} (pass mark 70%) · ") + time_note)
    print()
    print(bold("What to fix"))
    for n, task, pct, results in rows:
        if pct < 100:
            print()
            print(dim(f"#{n}"), end=" ")
            print_results(task, results, None, failures_only=True)
    state["sessions"].append({"kind": s["kind"], "name": s["name"], "score": round(overall, 1),
                              "passed": passed, "elapsed": round(elapsed),
                              "at": datetime.now().isoformat(timespec="seconds"),
                              "tasks": [{"slug": t.slug, "score": round(p, 1)} for _, t, p, _ in rows]})
    state["session"] = None
    save_state(state)
    print()
    print(dim("Your work is still in the server for review. Solutions: `chlab solution <task id>`. "
              "Task ids: " + ", ".join(f"#{n}={t.id}" for n, t, _, _ in rows)))


def cmd_abandon(args):
    state = load_state()
    s = state.get("session")
    if not s:
        die("Nothing to abandon.")
    if ch.ping():
        by_id = _tasks_by_id()
        for tid in s["tasks"]:
            T.reset(by_id[tid])
    state["session"] = None
    save_state(state)
    print(f"{s['name']} abandoned; nothing was graded.")

# --------------------------------------------------------- progress ----


def cmd_history(args):
    state = load_state()
    if not state["history"] and not state["sessions"]:
        print("No attempts yet.")
        return
    by_slug = {t.slug: t for t in T.load_all()}
    if state["sessions"]:
        print(bold("Mock exams and sprints"))
        for s in state["sessions"][-10:]:
            mark = green("PASS") if s["passed"] else red("not yet")
            print(f"  {s['at'][:16].replace('T', ' ')}  {s['name']:<34} {s['score']:>4.0f}%  {mark}  "
                  f"{dim(mmss(s['elapsed']))}")
        print()
    print(bold("Tasks"))
    for slug, attempts in state["history"].items():
        t = by_slug.get(slug)
        title = f"{t.id} · {t.title}" if t else slug
        scores = "  ".join(pct_color(a["score"]) for a in attempts[-8:])
        print(f"  {title}\n    {scores}")


def latest_scores(state: dict) -> dict[str, float]:
    return {slug: h[-1]["score"] for slug, h in state["history"].items() if h}


def cmd_report(args):
    state = load_state()
    tasks = T.load_all()
    latest = latest_scores(state)
    print(bold("Readiness by exam objective") + dim("  (latest score on each task, averaged)"))
    obj_scores = {}
    current_letter = None
    for code in OBJ.exam_codes():
        if code[0] != current_letter:
            current_letter = code[0]
            print()
            print(bold(OBJ.DOMAINS[current_letter]))
        covering = [t for t in tasks if code in t.objectives]
        tried = [latest[t.slug] for t in covering if t.slug in latest]
        score = sum(tried) / len(tried) if tried else 0
        obj_scores[code] = score
        label = textwrap.shorten(OBJ.OBJECTIVES[code], 52, placeholder="…")
        cov = dim(f"{len(tried)}/{len(covering)} tasks")
        print(f"  {code:<3} {label:<53} {bar(score, 12)} {pct_color(score, f'{score:>4.0f}%') if tried else dim('  --')}  {cov}")
    readiness = sum(obj_scores.values()) / len(obj_scores)
    print()
    print(bold(f"Overall readiness: ") + pct_color(readiness) +
          dim("  (untried objectives count as 0%)"))
    if state["sessions"]:
        last = [s for s in state["sessions"] if s["kind"] == "mock exam"][-3:]
        if last:
            print(bold("Recent mock exams: ") +
                  ", ".join(pct_color(s["score"]) for s in last))
    weakest = sorted(obj_scores, key=lambda c: obj_scores[c])[:3]
    print()
    print(bold("Practise next"))
    for code in weakest:
        covering = [t for t in tasks if code in t.objectives]
        covering.sort(key=lambda t: (latest.get(t.slug, -1), t.tier))
        if covering:
            t = covering[0]
            print(f"  {code}  {OBJ.OBJECTIVES[code]}\n      → `chlab start {t.id}` ({t.title})")
    speed = [h for hs in state["history"].values() for h in hs if h.get("mode") == "speed" and h["score"] >= 100]
    if speed:
        print()
        print(bold("Fastest perfect speed run: ") + mmss(min(h["elapsed"] for h in speed)))

# --------------------------------------------------------- authoring ----


def lint() -> list[str]:
    problems = []
    tasks = T.load_all()
    seen_ids, seen_slugs, seen_dbs, seen_views = {}, {}, {}, {}
    sets = yaml.safe_load(EXAMS_FILE.read_text())["exams"] if EXAMS_FILE.exists() else []
    for t in tasks:
        where = t.path.name
        if t.id in seen_ids:
            problems.append(f"{where}: id {t.id} also used by {seen_ids[t.id]}")
        seen_ids[t.id] = where
        if t.slug in seen_slugs:
            problems.append(f"{where}: slug {t.slug} also used by {seen_slugs[t.slug]}")
        seen_slugs[t.slug] = where
        if not t.path.name.startswith(f"{t.id:03d}-{t.slug}"):
            problems.append(f"{where}: file name should be {t.id:03d}-{t.slug}.yaml")
        if t.tier not in (1, 2, 3, 4):
            problems.append(f"{where}: tier must be 1-4")
        for d in t.domains:
            if d not in T.DOMAINS:
                problems.append(f"{where}: unknown domain {d}")
        for o in t.objectives:
            if o not in OBJ.OBJECTIVES:
                problems.append(f"{where}: unknown objective code {o}")
        if not t.databases:
            problems.append(f"{where}: reset must drop at least one database the task owns")
        for db in t.databases:
            if db in seen_dbs:
                problems.append(f"{where}: database {db} also owned by {seen_dbs[db]} (tasks share a server in exams)")
            seen_dbs[db] = where
        for stmt in t.reset:
            m = re.match(r"\s*DROP VIEW IF EXISTS\s+answers\.(\w+)", stmt, re.I)
            if m:
                if m.group(1) in seen_views:
                    problems.append(f"{where}: answers.{m.group(1)} also used by {seen_views[m.group(1)]}")
                seen_views[m.group(1)] = where
        names = [c["name"] for c in t.checks]
        if len(names) != len(set(names)):
            problems.append(f"{where}: check names must be unique")
        for c in t.checks:
            if c.get("type") not in grader.CHECKS:
                problems.append(f"{where}: check '{c.get('name')}' has unknown type {c.get('type')}")
        for w in t.wrong_solutions:
            for n in w["must_fail"]:
                if n not in names:
                    problems.append(f"{where}: wrong solution '{w['name']}' names unknown check '{n}'")
        if t.points <= 0:
            problems.append(f"{where}: checks carry no points")
    for s in sets:
        for i in s["tasks"]:
            if i not in seen_ids:
                problems.append(f"exams.yaml: set {s['id']} lists unknown task {i}")
    return problems


def cmd_lint(args):
    problems = lint()
    for p in problems:
        print(red("✘ ") + p)
    if problems:
        die(f"{len(problems)} lint problem(s).")
    print(green(f"✔ {len(T.load_all())} tasks pass lint."))


def _run_and_grade(task: T.Task, script: str):
    T.prepare(task, seed=random.randint(1, 1_000_000))
    proc = ch.run_script(T.fill(script))
    if proc.returncode != 0:
        return None, proc.stderr.strip()
    return grader.grade(task), ""


def cmd_selftest(args):
    """For task authors and CI: every reference solution and alternative must score 100%,
    and every known-wrong solution must lose the checks it names."""
    problems = lint()
    if problems:
        for p in problems:
            print(red("✘ ") + p)
        die(f"{len(problems)} lint problem(s).")
    require_server()
    chosen = [T.find(k) for k in args.tasks] if args.tasks else T.load_all()
    failures = 0
    started = time.time()
    for task in chosen:
        t0 = time.time()
        results, err = _run_and_grade(task, task.solution)
        if results is None:
            print(red(f"✘ {task.id:>2} {task.slug}: reference solution errored: ") + grader.short_error(err))
            failures += 1
        else:
            earned, total = grader.score(results)
            if earned < total:
                failures += 1
                print(red(f"✘ {task.id:>2} {task.slug}: reference solution scored {earned:g}/{total}"))
                for r in results:
                    if not r.passed:
                        print(f"     - {r.name}: {r.detail}")
            else:
                print(green(f"✔ {task.id:>2} {task.slug}: reference {earned:g}/{total}"))
        for alt in task.alternatives:
            results, err = _run_and_grade(task, alt["sql"])
            if results is None:
                failures += 1
                print(red(f"    ✘ alternative '{alt['name']}' errored: ") + grader.short_error(err))
                continue
            earned, total = grader.score(results)
            if earned < total:
                failures += 1
                lost = [f"{r.name}: {r.detail}" for r in results if not r.passed]
                print(red(f"    ✘ alternative '{alt['name']}' scored {earned:g}/{total}: {lost}"))
            else:
                print(green(f"    ✔ alternative '{alt['name']}'"))
        for wrong in task.wrong_solutions:
            results, err = _run_and_grade(task, wrong["sql"])
            if results is None:
                print(red(f"    ✘ wrong '{wrong['name']}' errored: ") + grader.short_error(err))
                failures += 1
                continue
            failed = {r.name for r in results if not r.passed}
            missing = [n for n in wrong["must_fail"] if n not in failed]
            if missing:
                failures += 1
                print(red(f"    ✘ wrong '{wrong['name']}' passed checks it should fail: {missing}"))
            else:
                print(green(f"    ✔ wrong '{wrong['name']}' caught") + dim(f" ({len(failed)} checks failed)"))
        T.reset(task)
        if args.timing:
            print(dim(f"    {time.time() - t0:.1f}s"))
    print()
    if failures:
        die(f"{failures} problem(s) found.")
    print(green(bold(f"All {len(chosen)} tasks verified")) + dim(f" in {time.time() - started:.0f}s."))


def cmd_site(args):
    from . import site
    out = Path(args.out).resolve()
    site.build(out)
    print(green(f"Site written to {out / 'index.html'}"))

# ------------------------------------------------------------------ main ----


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="chlab",
        description="ClickHouse Dev Lab: hands-on practice for the ClickHouse Certified Developer exam "
                    "(unofficial).")
    p.add_argument("--version", action="version", version=f"chlab {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="<command>")

    def add(name, fn, help_):
        s = sub.add_parser(name, help=help_)
        s.set_defaults(fn=fn)
        return s

    add("up", cmd_up, "start ClickHouse and the S3 stand-in")
    add("down", cmd_down, "stop them")
    s = add("list", cmd_list, "list tasks and your best scores")
    s.add_argument("--all", action="store_true", help="include stretch tasks")
    s = add("start", cmd_start, "start one task with fresh data")
    s.add_argument("task", help="task number or slug")
    add("speed", cmd_speed, f"random tier-1 task against a {SPEED_MINUTES}-minute clock")
    s = add("exam", cmd_exam, f"start a {EXAM_MINUTES}-minute mock exam (10-12 tasks)")
    s.add_argument("--set", help="a fixed mock exam from exams.yaml (1, 2, 3); default is random")
    s = add("sprint", cmd_sprint, f"{SPRINT_MINUTES}-minute set of tasks from one exam domain")
    s.add_argument("domain", help="modeling, inserting, analyzing, optimizing or dedup")
    add("status", cmd_status, "what is in progress, and time left")
    s = add("brief", cmd_brief, "show the current task (or task n of a mock exam/sprint)")
    s.add_argument("n", nargs="?", type=int)
    add("client", cmd_client, "open clickhouse-client (extra arguments are passed through)")
    add("check", cmd_check, "grade the current task")
    add("submit", cmd_submit, "grade a mock exam or sprint")
    add("abandon", cmd_abandon, "end a mock exam or sprint without grading")
    s = add("solution", cmd_solution, "show a task's reference solution")
    s.add_argument("task")
    s = add("reset", cmd_reset, "drop everything a task created (or `all`)")
    s.add_argument("task")
    add("history", cmd_history, "your scores so far")
    add("report", cmd_report, "readiness per exam objective, and what to practise next")
    add("lint", cmd_lint, "(authors) check task files for mistakes")
    s = add("selftest", cmd_selftest, "(authors/CI) verify tasks against their solutions")
    s.add_argument("tasks", nargs="*")
    s.add_argument("--timing", action="store_true")
    s = add("site", cmd_site, "(authors/CI) build the static website")
    s.add_argument("--out", default="site")

    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["client"]:
        # Everything after `client` belongs to clickhouse-client, untouched.
        return cmd_client(argparse.Namespace(extra=argv[1:]))
    args = p.parse_args(argv)
    if not getattr(args, "fn", None):
        p.print_help()
        return
    try:
        args.fn(args)
    except BrokenPipeError:  # output piped into `head` etc. (must come before ConnectionError)
        sys.stderr.close()
    except (KeyError, ConnectionError) as e:
        die(str(e).strip("'\""))


if __name__ == "__main__":
    main()
