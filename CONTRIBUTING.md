# Writing a task

Each task is one file in `tasks/`, named `NNN-slug.yaml`. Copy an existing task as a starting point.

## Ground rules

- Write tasks from the [published exam objectives](https://clickhouse.com/learn/certification) and the public docs only.
  Never submit anything based on real exam content.
- Grade outcomes, not syntax. A check should pass for every correct approach.
- Generate data with SQL from `{seed}`, so every attempt gets fresh values and nobody can memorise answers.
  Compute expected values from the data at grading time instead of hard-coding them.
- Keep data small enough to start in seconds on a laptop (under about 2M rows per task; 4M at most).
- Own your databases: every task drops and creates its own, uniquely named databases, because a mock exam
  loads 11 tasks into the same server. Answer views go in the shared `answers` database under unique names.
  `chlab lint` enforces both.

## Fields

| Field | Meaning |
| --- | --- |
| `id`, `slug`, `title` | Number, short name, title |
| `domains` | Any of `modeling`, `inserting`, `analyzing`, `optimizing`, `dedup` |
| `objectives` | Objective codes the task practises (`M1`...`D3`, stretch `S1`...`S4`; see `chlab/objectives.py`) |
| `tier`, `minutes` | Difficulty 1–4 and the time target |
| `docs` | Helpful doc pages (clickhouse.com only) |
| `brief` | What the candidate reads. State every name they must use |
| `reset` | Statements that remove everything the task or a previous attempt created |
| `setup` | Statements that build the starting state |
| `files` | Files to put in `/data`: `path`, `format`, a `query` that produces them, optional `compress: gzip` |
| `checks` | What the grader verifies (below) |
| `solution` | The reference solution, run through `clickhouse-client` |
| `alternatives` | Other correct solutions; each must also score 100% |
| `wrong_solutions` | Common mistakes; each lists the checks it `must_fail` |

## Placeholders

Use these anywhere (brief, setup, files, checks, solutions):

| Placeholder | Becomes |
| --- | --- |
| `{seed}` | A random number per attempt (setup and files only). Mix it into `cityHash64(...)` to vary the data |
| `{s3}` | The practice bucket URL as ClickHouse sees it, e.g. `http://s3:5000/chlab-data` |
| `{s3_key}`, `{s3_secret}` | Credentials for the bucket |

To put files in S3, write them from setup with
`INSERT INTO FUNCTION s3('{s3}/path/file.parquet', '{s3_key}', '{s3_secret}', 'Parquet') SELECT ...`.
Objects are overwritten on every start.

## Check types

| Type | Fields | Passes when |
| --- | --- | --- |
| `sql_true` | `query`, optional `show` | `query` returns 1. On failure, `show`'s result is printed as "Found: ..." |
| `column_types` | `table`, `columns: {name: [regex, ...]}` | Each column's type fully matches one regex (partial credit per column) |
| `granules` | `query`, `max_ratio`, optional `stage: final` | `EXPLAIN indexes = 1` leaves at most that share of granules (primary key only; with `stage: final`, after skipping indexes too) |
| `explain_contains` | `query`, `text`, optional `explain` | The EXPLAIN plan mentions `text`, e.g. `ReadFromMergeTree (my_projection)` |
| `result` | `query`, `expect`, optional `ordered`, `tolerance`, `columns` | Both queries return the same rows |

Every check has `name`, `points` and an optional `hint` shown on failure. Any check can have `prepare`
and `cleanup` statement lists. Do behaviour tests on a copy (`CREATE TABLE chlab_grader.x AS db.t`) so
the candidate's data is never touched. `chlab_grader` is dropped after grading.

In any check's SQL, `{as_select:db.view}` is replaced by the view's stored SELECT, and
`{as_select:db.view|db.table=>chlab_grader.copy}` also points it at a copy of the table. Use this to test a
candidate's view against data you control, such as unmerged duplicates.

## Traps learned the hard way

- `uniq()` is exact below about 65,000 distinct values. Use more if a check must tell it from `uniqExact()`.
- ReplacingMergeTree and CollapsingMergeTree deduplicate **within a single INSERT**. To test "correct before merges",
  load a copy in several inserts with `SYSTEM STOP MERGES`.
- Within one INSERT into a CollapsingMergeTree, a new state placed before its cancel row collapses away.
- An `ALTER ... UPDATE/DELETE ... SETTINGS mutations_sync = 1` on a table with merges stopped never returns.
- Quote any YAML value containing `: ` (use a `|` block), or the file will not load.

## Test it

```bash
chlab up
chlab lint              # unique ids, databases, valid objective codes...
chlab selftest <slug>   # reference and alternatives must score 100%, wrong solutions must be caught
chlab start <id>        # then try it yourself in the client
```

To add a task to a fixed mock exam, edit `exams.yaml`.

Pull requests run `chlab selftest` for every task in CI.
