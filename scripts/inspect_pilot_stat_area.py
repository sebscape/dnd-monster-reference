#!/usr/bin/env python3
"""Inspect exact pilot stat-block lines, including unlabeled ability rows."""
import json
from pathlib import Path

root = Path("staging/srd-5.2.1")
data = json.loads((root / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))
names = {"Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat"}
lines = ["PILOT RAW STAT AREA — REVIEW ONLY", ""]
for record in data["records"]:
    if record["name"] not in names:
        continue
    lines.append("=== " + record["name"] + " ===")
    raw = record["cleaned_excerpt"].splitlines()
    for index, line in enumerate(raw[:42], 1):
        lines.append(f"{index:02d}: {line!r}")
    lines.append("")
lines.append("Original and published/custom records unchanged.")
output = root / "pilot-raw-stat-area.txt"
output.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Report: {output}")
print("No published or custom monsters were modified.")
