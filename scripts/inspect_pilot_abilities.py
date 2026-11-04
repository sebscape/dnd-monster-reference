#!/usr/bin/env python3
"""Show raw ability-score and secondary-stat lines for five pilot monsters."""
import json
from pathlib import Path

root = Path("staging/srd-5.2.1")
data = json.loads((root / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))
wanted = {"Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat"}
report = ["SRD pilot ability/stat layout inspection — NOT FOR IMPORT", ""]
for record in data["records"]:
    if record["name"] not in wanted:
        continue
    lines = record["cleaned_excerpt"].splitlines()
    report.append("=== " + record["name"] + " ===")
    for index, line in enumerate(lines):
        stripped = line.strip()
        if any(token in stripped for token in ("STR", "DEX", "CON", "INT", "WIS", "CHA", "Saving Throws", "Skills", "Senses", "Languages", "Immunities", "Resistances", "Vulnerabilities")):
            start = max(0, index - 1)
            end = min(len(lines), index + 4)
            report.extend(f"  [{j + 1}] {lines[j]}" for j in range(start, end))
            report.append("  ---")
    report.append("")
report.append("No published or custom monsters were modified.")
path = root / "pilot-ability-layout-report.txt"
path.write_text("\n".join(report) + "\n", encoding="utf-8")
print(f"Report: {path}")
print("No published or custom monsters were modified.")
