#!/usr/bin/env python3
"""Audit secondary stat fields on five cleaned SRD excerpts. Review only.

Preserves source text; continuation lines are joined only within the header
region before CR. Immunities are retained verbatim, not split speculatively.
"""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
PILOTS = ["Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat"]
FIELDS = ["Skills", "Senses", "Languages", "Vulnerabilities", "Resistances", "Immunities", "Gear"]
FIELD_PATTERN = re.compile(r"^(" + "|".join(FIELDS) + r")\s+(.+)$")

def parse_secondary(record):
    lines = record["cleaned_excerpt"].splitlines()
    cr_index = next((i for i, line in enumerate(lines) if re.match(r"^CR\s+", line.strip())), len(lines))
    values = {}
    notes = []
    current = None
    for line in lines[:cr_index]:
        text = line.strip()
        match = FIELD_PATTERN.match(text)
        if match:
            key, value = match.groups()
            if key in values:
                notes.append(f"Repeated field: {key}")
            values[key] = (values.get(key, "") + " " + value).strip()
            current = key
        elif current and text:
            if re.match(r"^(?:AC|HP|Speed|Initiative|MOD SAVE|Str|Dex|Con|Int|Wis|Cha)\b", text):
                current = None
            else:
                values[current] += " " + text
    return values, notes

def main():
    data = json.loads((ROOT / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))
    records = {r["name"]: r for r in data["records"]}
    report = ["SRD secondary-stat pilot audit — UNVERIFIED / NOT FOR IMPORT", ""]
    for name in PILOTS:
        if name not in records:
            raise SystemExit(f"Missing pilot: {name}")
        fields, notes = parse_secondary(records[name])
        report.append(f"=== {name} ===")
        for field in FIELDS:
            report.append(f"  {field}: {fields.get(field, '[not present]')}")
        report.append("  Review notes: " + ("; ".join(notes) if notes else "none"))
        report.append("")
    report.append("Immunities are verbatim; damage/condition split requires review.")
    report.append("No published or custom monsters were modified.")
    output = ROOT / "pilot-secondary-stats-report.txt"
    output.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Pilot monsters: {len(PILOTS)}")
    print(f"Report: {output}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
