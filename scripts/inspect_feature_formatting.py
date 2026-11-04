#!/usr/bin/env python3
"""Review representative SRD feature text and monsters without Actions.

Staging-only diagnostic; does not modify original or catalog records.
"""
import json
import re
from pathlib import Path

root = Path("staging/srd-5.2.1")
data = json.loads((root / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))
records = data["records"]
headings = {"Traits", "Actions", "Bonus Actions", "Reactions", "Legendary Actions"}
samples = {"Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat",
           "Ancient Bronze Dragon", "Cloud Giant", "Ancient Copper Dragon"}
report = ["SRD feature formatting inspection — NOT FOR IMPORT", ""]
missing = []
for record in records:
    lines = record["cleaned_excerpt"].splitlines()
    if not any(line.strip() == "Actions" for line in lines):
        missing.append(record["name"])
    if record["name"] not in samples:
        continue
    report.append("=== " + record["name"] + " ===")
    start = next((i for i, line in enumerate(lines) if line.strip() in headings), None)
    if start is None:
        report.append("  No recognized feature heading")
    else:
        for i, line in enumerate(lines[start:start + 70], start + 1):
            report.append(f"  {i:03d}: {line!r}")
    report.append("")
report.insert(2, "Monsters without Actions heading: " + (", ".join(missing) if missing else "none"))
report.extend(["", "No published or custom monsters were modified."])
output = root / "feature-formatting-review.txt"
output.write_text("\n".join(report) + "\n", encoding="utf-8")
print("Monsters without Actions heading: " + (", ".join(missing) if missing else "none"))
print(f"Report: {output}")
print("No published or custom monsters were modified.")
