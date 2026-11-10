# Start here

Welcome. This is a **free, unofficial practice ground for the ClickHouse Certified Developer
exam**. The real exam is 100% hands-on in `clickhouse-client`; so is this. Nothing here matches
real exam questions, the tasks are written from the
[published objectives](https://clickhouse.com/learn/certification) and the public docs.

If you opened this in a Codespace, ClickHouse is already running. If you are on your own
machine, run `chlab up` once.

---

## The loop (do this 36 times)

```bash
chlab list        # browse the tasks and your best score on each
chlab start 1     # reset task 1, generate fresh data, show the brief, start the clock
chlab client      # open clickhouse-client — this is where you work
chlab check       # grade yourself against the server's real state
chlab solution 1  # the reference solution (try before peeking)
```

Rules of a good rep:

1. **Docs only.** Keep <https://clickhouse.com/docs> open. No AI, no search engines — the real
   exam allows the docs and nothing else, so train that way.
2. **Respect the clock.** Each brief shows a target time. The exam gives you 2 hours for 10–12
   tasks; the per-task targets add up to that.
3. **Only `chlab solution` after `chlab check`** and a genuine attempt.

## Then take mock exams

```bash
chlab exam            # 11 tasks, 120 minutes, random each time
chlab exam --set 1    # a fixed set (1, 2 or 3)
```

During a mock exam, `chlab check` and solutions are locked (just like the real thing). Use
`chlab brief <n>` to read a task and `chlab submit` at the end. Want one domain only?

```bash
chlab sprint modeling    # or inserting / analyzing / optimizing / dedup
chlab speed              # a tier-1 task against a 5-minute clock
```

## Track readiness

```bash
chlab report      # your score per exam objective + what to practise next
chlab history     # every attempt
```

Book the real exam when you clear **80%+ on two mock exams in a row**.

## Where your files are

Task data lives in `/data`. Read it in the client like this:

```sql
INSERT INTO db.table FROM INFILE '/data/file.csv' FORMAT CSVWithNames;
SELECT * FROM file('/data/file.csv', 'CSVWithNames') LIMIT 5;
```

Cloud-storage tasks use a local S3-compatible server; each brief gives the URL and keys.

## Saving your free hours

A Codespace on the default 2-core machine draws on your GitHub free monthly allowance
(about 60 hours). **Stop the Codespace when you stop practising**: the Codespaces menu →
*Stop current codespace*, or close the browser tab and stop it from <https://github.com/codespaces>.
Your scores live in the Codespace's disk and survive a stop/start; they do not follow you to a
new machine.

## Not affiliated with ClickHouse, Inc.

This is a community project. ClickHouse is a trademark of ClickHouse, Inc. See the README for
the full disclaimer.