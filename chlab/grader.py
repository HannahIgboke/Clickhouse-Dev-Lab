"""The grader: inspects the final state of the server and scores each check.

It never looks at what you typed, only at what exists and what it returns,
so any correct approach scores full marks.

Check types (in a task's `checks:` list):

  sql_true      query must return 1 (or true). Optional `show`: a query whose
                result is printed on failure ("found: ...").
  column_types  table + {column: [allowed type regex, ...]}. Partial credit per column.
  granules      Runs EXPLAIN indexes = 1 on `query`; the primary key must leave at
                most `max_ratio` of granules to read (`stage: final` = after skip
                indexes too).
  explain_contains  The EXPLAIN plan of `query` mentions `text` (e.g. a projection).
  result        Compares the rows of `query` with the rows of `expect`
                (`ordered`, relative `tolerance`, optional exact `columns`).

Any check may also carry `prepare:` and `cleanup:` statement lists, and its SQL
may use {as_select:db.view} or {as_select:db.view|db.table=>db.clone} to reuse
the SELECT stored in a view you created (optionally pointed at another table).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from . import ch
from .tasks import Task, fill

PASS_MARK = 0.70


@dataclass
class CheckResult:
    name: str
    points: int
    earned: float
    detail: str = ""
    hint: str = ""

    @property
    def passed(self) -> bool:
        return self.earned >= self.points - 1e-9


class CheckFailed(Exception):
    def __init__(self, detail: str, fraction: float = 0.0):
        super().__init__(detail)
        self.detail = detail
        self.fraction = fraction


def short_error(msg: str) -> str:
    """Turn a ClickHouse error into the part a human needs."""
    msg = msg.strip()
    if msg.startswith("{"):
        try:
            msg = json.loads(msg).get("exception", msg)
        except ValueError:
            pass
    msg = msg.splitlines()[0] if msg else msg
    for pattern, text in (
        (r"Unknown table expression identifier '([^']+)'", "{} does not exist yet."),
        (r"Table (\S+) does not exist", "{} does not exist yet."),
        (r"Database (\S+) does not exist", "Database {} does not exist yet."),
        (r"external dictionary '([^']+)' not found", "Dictionary {} does not exist yet."),
        (r"Dictionary \(?`?([\w.`]+)`?\)? not found", "Dictionary {} does not exist yet."),
    ):
        m = re.search(pattern, msg)
        if m:
            return text.format(m.group(1).replace("`", "").rstrip("."))
    msg = re.sub(r"^Code: \d+\. DB::Exception: ", "", msg)
    msg = re.sub(r"\s*\(version .*\)\s*$", "", msg, flags=re.I)
    msg = re.sub(r"\s*\([A-Z_]+\)\s*$", "", msg)
    msg = re.sub(r" in scope SELECT .*$", "", msg)
    return msg[:300]


_AS_SELECT = re.compile(r"\{as_select:([\w.]+)(?:\|([\w.]+)=>([\w.]+))?\}")


def _expand(sql: str) -> str:
    sql = fill(sql)

    def repl(m: re.Match) -> str:
        db, _, name = m.group(1).partition(".")
        row = ch.rows(
            f"SELECT engine, as_select FROM system.tables "
            f"WHERE database = '{db}' AND name = '{name}'")
        if not row:
            raise CheckFailed(f"{m.group(1)} does not exist.")
        if row[0]["engine"] not in ("View", "MaterializedView"):
            raise CheckFailed(f"{m.group(1)} exists but is a {row[0]['engine']} table, not a view.")
        select = row[0]["as_select"]
        if m.group(2):
            src, dst = m.group(2), m.group(3)
            s_db, _, s_tbl = src.partition(".")
            d_db, _, d_tbl = dst.partition(".")
            pattern = rf"`?{re.escape(s_db)}`?\s*\.\s*`?{re.escape(s_tbl)}`?(?![\w`])"
            if not re.search(pattern, select):
                raise CheckFailed(f"The view {m.group(1)} does not read from {src}.")
            select = re.sub(pattern, f"{d_db}.{d_tbl}", select)
        return f"({select})"
    return _AS_SELECT.sub(repl, sql)


def _check_sql_true(c: dict) -> None:
    value = ch.scalar(_expand(c["query"]))
    if value in (1, True, "1", "true"):
        return
    found = ""
    if c.get("show"):
        try:
            shown = ch.rows(_expand(c["show"]))
            found = ", ".join(str(list(r.values())[0] if len(r) == 1 else tuple(r.values()))
                              for r in shown) or "nothing"
        except (ch.ClickHouseError, CheckFailed):
            found = "nothing"
    raise CheckFailed(f"Found: {found}." if c.get("show") else "Condition not met.")


def _check_column_types(c: dict) -> None:
    db, _, table = c["table"].partition(".")
    actual = {r["name"]: r["type"] for r in ch.rows(
        f"SELECT name, type FROM system.columns WHERE database = '{db}' AND table = '{table}'")}
    if not actual:
        raise CheckFailed(f"Table {c['table']} does not exist.")
    wanted = c["columns"]
    bad = []
    for col, patterns in wanted.items():
        t = actual.get(col)
        if t is None:
            bad.append(f"{col}: missing")
        elif not any(re.fullmatch(p, t) for p in patterns):
            bad.append(f"{col}: {t}")
    if bad:
        good = len(wanted) - len(bad)
        raise CheckFailed("Not the most efficient type: " + "; ".join(bad) + ".",
                          fraction=good / len(wanted))


def _check_granules(c: dict) -> None:
    """Primary key pruning by default; with `stage: final`, the last Granules line
    (after skipping indexes and projections have had their say)."""
    plan = ch.text("EXPLAIN indexes = 1 " + _expand(c["query"]))
    lines = [l.strip() for l in plan.splitlines()]
    found = None
    if c.get("stage") == "final":
        grans = [l for l in lines if l.startswith("Granules:")]
        found = grans[-1] if grans else None
    else:
        in_pk = False
        for l in lines:
            if l == "PrimaryKey":
                in_pk = True
            elif in_pk and l.startswith("Granules:"):
                found = l
                break
    if not found:
        raise CheckFailed("No index is used for this query at all.")
    read, total = (int(x) for x in found.split(":", 1)[1].split("/"))
    ratio = read / total if total else 1.0
    if ratio <= c["max_ratio"]:
        return
    what = "After all indexes, the query" if c.get("stage") == "final" else "The primary key"
    raise CheckFailed(
        f"{what} leaves {read} of {total} granules to read ({ratio:.0%}); "
        f"the target is {c['max_ratio']:.0%} or less.")


def _check_explain_contains(c: dict) -> None:
    """The EXPLAIN plan of `query` must mention `text` (e.g. a projection's name)."""
    plan = ch.text(f"EXPLAIN {c.get('explain', 'indexes = 1')} " + _expand(c["query"]))
    if c["text"] in plan:
        return
    reads = [l.strip() for l in plan.splitlines() if "ReadFromMergeTree" in l]
    raise CheckFailed(f"The plan does not use {c['text']}. It shows: {'; '.join(reads) or 'no table read'}.")


def _same(a, b, tol: float) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if tol == 0:
            return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
    return str(a) == str(b)


def _check_result(c: dict) -> None:
    got = ch.rows(_expand(c["query"]))
    want = ch.rows(_expand(c["expect"]))
    if c.get("columns"):
        names = list(got[0].keys()) if got else [
            r["name"] for r in ch.rows("DESCRIBE (" + _expand(c["query"]) + ")")]
        if names != c["columns"]:
            raise CheckFailed(f"Columns should be {c['columns']}, found {names}.")
    tol = float(c.get("tolerance", 0))
    g = [tuple(r.values()) for r in got]
    w = [tuple(r.values()) for r in want]
    if len(g) != len(w):
        raise CheckFailed(f"Expected {len(w)} rows, got {len(g)}.")
    if not c.get("ordered", True):
        g, w = sorted(g, key=str), sorted(w, key=str)
    for i, (gr, wr) in enumerate(zip(g, w), start=1):
        if len(gr) != len(wr) or not all(_same(x, y, tol) for x, y in zip(gr, wr)):
            raise CheckFailed(f"Row {i}: expected {wr}, got {gr}.")


CHECKS = {
    "sql_true": _check_sql_true,
    "column_types": _check_column_types,
    "granules": _check_granules,
    "explain_contains": _check_explain_contains,
    "result": _check_result,
}


def grade(task: Task) -> list[CheckResult]:
    results = []
    for c in task.checks:
        points = int(c.get("points", 0))
        res = CheckResult(name=c["name"], points=points, earned=0, hint=c.get("hint", ""))
        try:
            for stmt in c.get("prepare", []):
                ch.execute(_expand(stmt))
            CHECKS[c["type"]](c)
            res.earned = points
        except CheckFailed as e:
            res.earned = round(points * e.fraction, 1)
            res.detail = e.detail
        except ch.ClickHouseError as e:
            res.detail = short_error(str(e))
        finally:
            for stmt in c.get("cleanup", []):
                try:
                    ch.execute(fill(stmt))
                except ch.ClickHouseError:
                    pass
        results.append(res)
    try:
        ch.execute("DROP DATABASE IF EXISTS chlab_grader SYNC")
    except ch.ClickHouseError:
        pass
    return results


def score(results: list[CheckResult]) -> tuple[float, int]:
    return sum(r.earned for r in results), sum(r.points for r in results)
