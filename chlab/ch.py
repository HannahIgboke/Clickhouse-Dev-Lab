"""Talking to ClickHouse.

Two channels:
* HTTP (port 8123) for setup and grading: one statement per request, JSON rows back.
* The real clickhouse-client, for the candidate's interactive session and for
  running reference solutions (they use client-only features such as FROM INFILE).
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
HTTP_URL = os.environ.get("CHLAB_HTTP", "http://localhost:8123")
USER = os.environ.get("CHLAB_USER", "default")
PASSWORD = os.environ.get("CHLAB_PASSWORD", "")

# S3-compatible storage (moto) for cloud-storage tasks.
# S3_URL is the bucket as ClickHouse sees it (inside Docker: the `s3` service);
# S3_HOST is the same server as seen from your machine, used only to create the bucket.
S3_URL = os.environ.get("CHLAB_S3_URL", "http://s3:5000/chlab-data").rstrip("/")
S3_HOST = os.environ.get("CHLAB_S3_HOST", "http://localhost:9002").rstrip("/")
S3_KEY = os.environ.get("CHLAB_S3_KEY", "chlab")
S3_SECRET = os.environ.get("CHLAB_S3_SECRET", "chlabsecret")


class ClickHouseError(Exception):
    """A query failed on the server. The message is ClickHouse's own."""


def _request(sql: str, params: dict | None = None, timeout: int = 300) -> bytes:
    query = {"default_format": "JSONEachRow",
             "output_format_json_quote_64bit_integers": "0",
             "output_format_json_quote_decimals": "0"}
    query.update(params or {})
    url = f"{HTTP_URL}/?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url, data=sql.encode("utf-8"), method="POST")
    req.add_header("X-ClickHouse-User", USER)
    if PASSWORD:
        req.add_header("X-ClickHouse-Key", PASSWORD)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace").strip()
        raise ClickHouseError(body) from None
    except urllib.error.URLError as e:
        raise ConnectionError(
            f"Cannot reach ClickHouse at {HTTP_URL} ({e.reason}). Is it running? Try `chlab up`."
        ) from None


def execute(sql: str, **settings) -> None:
    """Run a statement that returns nothing useful (DDL, INSERT)."""
    _request(sql, {k: str(v) for k, v in settings.items()})


def rows(sql: str, **settings) -> list[dict]:
    """Run a SELECT and return its rows as dicts (column order preserved)."""
    out = _request(sql, {k: str(v) for k, v in settings.items()}).decode("utf-8")
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def scalar(sql: str, **settings):
    result = rows(sql, **settings)
    if not result:
        return None
    return next(iter(result[0].values()))


def text(sql: str) -> str:
    """Run a query and return raw TabSeparatedRaw text (used for EXPLAIN)."""
    return _request(sql, {"default_format": "TSVRaw"}).decode("utf-8")


def download(sql: str, dest: Path) -> int:
    """Run a query that ends in FORMAT ... and write its output to a file."""
    data = _request(sql)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


def ping() -> bool:
    try:
        with urllib.request.urlopen(f"{HTTP_URL}/ping", timeout=3) as resp:
            return resp.read().strip() == b"Ok."
    except Exception:
        return False


def ensure_bucket() -> None:
    """Create the practice bucket (idempotent). The S3 stand-in keeps data in memory."""
    bucket = S3_URL.rsplit("/", 1)[1]
    req = urllib.request.Request(f"{S3_HOST}/{bucket}", method="PUT", data=b"")
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except urllib.error.HTTPError as e:
        if e.code != 409:  # 409 = already exists
            raise ConnectionError(f"Could not create the S3 bucket at {S3_HOST} (HTTP {e.code}).") from None
    except urllib.error.URLError as e:
        raise ConnectionError(
            f"Cannot reach the S3 service at {S3_HOST} ({e.reason}). Is it running? Try `chlab up`.") from None


def client_command(interactive: bool) -> list[str]:
    """The command that opens clickhouse-client.

    Default: the client inside the Docker container (what candidates use).
    Override with CHLAB_CLIENT, e.g. CHLAB_CLIENT="clickhouse client" for a local install.
    """
    override = os.environ.get("CHLAB_CLIENT")
    if override:
        return shlex.split(override)
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), "exec"]
    if not interactive:
        cmd.append("-T")
    return cmd + ["clickhouse", "clickhouse-client"]


def run_script(sql: str) -> subprocess.CompletedProcess:
    """Feed a multi-statement SQL script to clickhouse-client on stdin."""
    cmd = client_command(interactive=False) + ["--multiquery"]
    try:
        return subprocess.run(cmd, input=sql, text=True, capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "Timed out after 300 s (a mutation waiting forever?)")
