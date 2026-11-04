#!/usr/bin/env python3
"""Audit ability parsing across every staged SRD excerpt; never import records."""
import json
from pathlib import Path
from parse_pilot_abilities import parse_abilities

root = Path("staging/srd-5.2.1")
source = root / "monster-excerpts-cleaned.json"
output = root / "all-ability-parsing-audit.txt"
data = json.loads(source.read_text(encoding="utf-8"))
records = data["records"]
if len(records) != 330:
    raise SystemExit(f"Expected 330 excerpts, got {len(records)}")
complete = 0
flagged = []
for record in records:
    parsed, issues = parse_abilities(record)
    if not issues and len(parsed) == 6:
        complete += 1
    else:
        flagged.append((record["name"], issues, parsed))
lines = [
    "SRD 5.2.1 — all-monster ability parsing audit (NOT FOR IMPORT)",
    f"Excerpts examined: {len(records)}",
    f"Complete, no flagged issues: {complete}",
    f"Needs review: {len(flagged)}",
    "",
    "REVIEW ITEMS:",
]
for name, issues, parsed in flagged:
    lines.append(f"- {name}: {', '.join(issues) if issues else 'Incomplete ability set'}")
    lines.append("  Parsed: " + ", ".join(sorted(parsed)))
lines += ["", "No published or custom monsters were modified."]
output.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Excerpts examined: {len(records)}")
print(f"Complete: {complete}")
print(f"Needs review: {len(flagged)}")
print(f"Report: {output}")
print("No published or custom monsters were modified.")
