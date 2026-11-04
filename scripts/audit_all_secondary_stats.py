#!/usr/bin/env python3
"""Audit secondary-stat parsing for all 330 staged SRD monsters; read-only."""
import json
from pathlib import Path
from parse_pilot_secondary_stats import parse_secondary, FIELDS

root = Path("staging/srd-5.2.1")
data = json.loads((root / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))
records = data["records"]
if len(records) != 330:
    raise SystemExit(f"Expected 330 records; found {len(records)}")
counts = {field: 0 for field in FIELDS}
issues = []
examples = []
for record in records:
    values, notes = parse_secondary(record)
    for field in values:
        counts[field] += 1
    if notes:
        issues.append((record["name"], notes))
    if "Immunities" in values:
        examples.append((record["name"], values["Immunities"]))
lines = [
    "SRD 5.2.1 secondary statistics — FULL CATALOG AUDIT",
    "UNVERIFIED / NOT FOR IMPORT",
    f"Excerpts examined: {len(records)}",
    f"Records with parser review notes: {len(issues)}",
    "",
    "Field presence counts (absence may be legitimate):",
]
lines.extend(f"  {field}: {counts[field]}" for field in FIELDS)
lines.extend(["", "PARSER REVIEW NOTES:"])
for name, notes in issues:
    lines.append(f"  {name}: {'; '.join(notes)}")
lines.extend(["", "IMMUNITIES SAMPLE (first 30):"])
for name, value in examples[:30]:
    lines.append(f"  {name}: {value}")
lines.extend([
    "",
    "Important: This audit does not prove every field was captured.",
    "Damage versus condition immunities have not been split.",
    "Original, published, and custom monsters were not modified.",
])
output = root / "all-secondary-stats-audit.txt"
output.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Excerpts examined: {len(records)}")
print(f"Parser review notes: {len(issues)}")
print(f"Report: {output}")
print("No published or custom monsters were modified.")
