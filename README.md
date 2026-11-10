# ClickHouse Dev Lab

Hands-on practice for the [ClickHouse Certified Developer exam](https://clickhouse.com/learn/certification).
Free, one-click, runs in your browser — real `clickhouse-client`, 36 auto-graded tasks,
mock exams covering all 21 official exam objectives.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/HannahIgboke/Clickhouse-Dev-Lab?quickstart=1)
[![Website](https://img.shields.io/badge/website-task%20catalogue-c2410c)](https://HannahIgboke.github.io/Clickhouse-Dev-Lab/)

Click the **"Open in GitHub Codespaces"** badge above and start within 30 seconds —
no Docker, no setup, no cost.

## Quick start

```bash
# List available tasks
chlab list

# Start a task
chlab start 1

# In another terminal, connect clickhouse-client
chlab client

# Check your solution
chlab check
```

See [START-HERE](docs/START-HERE.md) for the full practice loop, mock exams,
and tips for saving free Codespaces hours.

## Run locally (Docker)

```bash
git clone https://github.com/HannahIgboke/Clickhouse-Dev-Lab.git
cd Clickhouse-Dev-Lab
pip install -e .
chlab up
```

## Project layout

| Path | Purpose |
| --- | --- |
| `chlab/cli.py` | CLI: start, check, list, exam, sprint, ... |
| `chlab/grader.py` | Auto-grading engine (outcome-based) |
| `chlab/tasks.py` | Data generation + task loading |
| `chlab/ch.py` | ClickHouse connection helpers |
| `chlab/site.py` | Static site generator for the task catalogue |
| `tasks/*.yaml` | 36 task definitions |
| `exams.yaml` | Mock exam configurations |
| `docs/` | Getting started, publishing, full plan |

## License

MIT — see [LICENSE](LICENSE).

*Unofficial — not affiliated with ClickHouse Inc.*