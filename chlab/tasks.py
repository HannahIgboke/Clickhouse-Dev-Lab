"""Loading tasks from tasks/*.yaml and preparing their environment."""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import ch

TASKS_DIR = ch.REPO_ROOT / "tasks"
DATA_DIR = ch.REPO_ROOT / "workspace" / "data"

DOMAINS = {
    "modeling": "Modeling data",
    "inserting": "Inserting data",
    "analyzing": "Analyzing data",
    "optimizing": "Optimizing query performance",
    "dedup": "Deduplication and mutations",
    "stretch": "Stretch",
}


def fill(text: str, seed: int | None = None) -> str:
    """Replace the placeholders tasks may use."""
    out = (text.replace("{s3}", ch.S3_URL)
               .replace("{s3_key}", ch.S3_KEY)
               .replace("{s3_secret}", ch.S3_SECRET))
    if seed is not None:
        out = out.replace("{seed}", str(seed))
    return out


@dataclass
class Task:
    id: int
    slug: str
    title: str
    domains: list[str]
    objectives: list[str]
    tier: int
    minutes: int
    brief: str
    reset: list[str]
    setup: list[str]
    files: list[dict]
    checks: list[dict]
    solution: str
    wrong_solutions: list[dict] = field(default_factory=list)
    alternatives: list[dict] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    path: Path | None = None

    @property
    def uses_s3(self) -> bool:
        blob = " ".join(self.setup) + self.solution + str(self.checks)
        return "{s3" in blob

    @property
    def databases(self) -> list[str]:
        found = []
        for stmt in self.reset:
            m = re.match(r"\s*DROP DATABASE IF EXISTS\s+`?(\w+)`?", stmt, re.I)
            if m:
                found.append(m.group(1))
        return found

    @property
    def stretch(self) -> bool:
        return "stretch" in self.domains

    @property
    def points(self) -> int:
        return sum(int(c.get("points", 0)) for c in self.checks)


def load_all() -> list[Task]:
    tasks = []
    for path in sorted(TASKS_DIR.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise SystemExit(f"error: {path.name} is not valid YAML:\n{e}") from None
        tasks.append(Task(
            id=int(raw["id"]), slug=raw["slug"], title=raw["title"],
            domains=raw["domains"], objectives=raw.get("objectives", []),
            tier=int(raw["tier"]), minutes=int(raw["minutes"]),
            brief=raw["brief"].strip(), reset=raw.get("reset", []),
            setup=raw.get("setup", []), files=raw.get("files", []),
            checks=raw["checks"], solution=raw["solution"].strip(),
            wrong_solutions=raw.get("wrong_solutions", []),
            alternatives=raw.get("alternatives", []),
            docs=raw.get("docs", []), path=path,
        ))
    return tasks


def find(key: str) -> Task:
    for t in load_all():
        if key == str(t.id) or key == t.slug:
            return t
    raise KeyError(f"No task '{key}'. Run `chlab list` to see the tasks.")


def reset(task: Task) -> None:
    """Drop everything the task (or a previous attempt) created."""
    for stmt in task.reset:
        ch.execute(fill(stmt))
    ch.execute("DROP DATABASE IF EXISTS chlab_grader SYNC")
    for f in task.files:
        (DATA_DIR / f["path"]).unlink(missing_ok=True)


def prepare(task: Task, seed: int) -> None:
    """Reset, then build the task's starting state: seed tables and files."""
    if task.uses_s3:
        ch.ensure_bucket()
    reset(task)
    for stmt in task.setup:
        ch.execute(fill(stmt, seed), s3_truncate_on_insert=1)
    for f in task.files:
        sql = fill(f["query"], seed).rstrip().rstrip(";")
        dest = DATA_DIR / f["path"]
        ch.download(f"{sql}\nFORMAT {f['format']}", dest)
        if f.get("compress") == "gzip":
            dest.write_bytes(gzip.compress(dest.read_bytes()))
