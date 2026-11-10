"""git filter-branch --msg-filter helper.

Reads a commit message on stdin and writes a cleaned message on stdout,
removing AI attribution trailers added by tooling.
"""
import re
import sys

DROP = re.compile(
    r"^\s*(Co-Authored-By:\s*Claude|Claude-Session:|"
    r"Generated with .*Claude|.*noreply@anthropic\.com)",
    re.IGNORECASE,
)

data = sys.stdin.read()
lines = [line for line in data.splitlines() if not DROP.match(line)]

# Trim trailing blank lines left behind by removed trailers.
while lines and not lines[-1].strip():
    lines.pop()

sys.stdout.write("\n".join(lines) + "\n")
