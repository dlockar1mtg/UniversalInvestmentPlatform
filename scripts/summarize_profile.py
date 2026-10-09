"""Summarise a py-spy raw (collapsed-stack) profile as GitHub notices: where the run spent its time.

Each line of the profile is `frame;frame;...;frame count`. A function's share is the fraction of samples
whose stack contains it (inclusive time). Only this repository's code and the database driver are listed.
"""
from __future__ import annotations

import re
import os
import sys
from collections import Counter
from pathlib import Path

WORKSPACE = os.environ.get("GITHUB_WORKSPACE", "")
FRAME = re.compile(r"^(?P<fn>.+?) \((?P<file>[^():]+)(?::\d+)?\)$")


def summarise(lines: list[str], top: int = 15) -> tuple[int, list[tuple[str, int]], list[tuple[str, int]]]:
    inclusive: Counter = Counter()
    leaf: Counter = Counter()
    total = 0
    for line in lines:
        stack, _, count = line.rstrip("\n").rpartition(" ")
        if not stack or not count.isdigit():
            continue
        n = int(count)
        total += n
        names = []
        for frame in stack.split(";"):
            m = FRAME.match(frame.strip())
            if not m:
                continue
            path = m.group("file")
            if ("site-packages" in path or "/lib/python" in path) and "psycopg" not in path:
                continue
            short = path.split("site-packages/")[-1]
            if WORKSPACE and short.startswith(WORKSPACE):
                short = short[len(WORKSPACE):].lstrip("/")
            names.append(f"{m.group('fn')} ({short})")
        for name in set(names):
            inclusive[name] += n
        if names:
            leaf[names[-1]] += n
    return total, inclusive.most_common(top), leaf.most_common(top)


def main(path: str) -> int:
    p = Path(path)
    if not p.is_file():
        print(f"No profile at {path}")
        return 0
    total, inc, leaf = summarise(p.read_text(encoding="utf-8", errors="replace").splitlines())
    if not total:
        print("Profile is empty")
        return 0
    rows = [f"{100 * n / total:5.1f}%  {name}" for name, n in inc]
    rows += ["-- deepest own frames --"] + [f"{100 * n / total:5.1f}%  {name}" for name, n in leaf[:8]]
    print("\n".join(rows))
    print("::notice title=Publish profile (" + str(total) + " samples)::" + "%0A".join(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "publish_profile.txt"))
