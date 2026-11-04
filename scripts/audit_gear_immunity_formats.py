#!/usr/bin/env python3
"""Inspect SRD gear and immunity formats before schema migration.

Staging-only diagnostic. Does not change published or custom monsters.
"""
import json
from collections import Counter
from pathlib import Path
from parse_pilot_secondary_stats import parse_secondary

ROOT = Path("staging/srd-5.2.1")
OUTPUT = ROOT / "gear-immunity-schema-review.txt"

def main():
    records = json.loads((ROOT / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))["records"]
    if len(records) != 330:
        raise SystemExit(f"Expected 330 monsters, got {len(records)}")
    gears = []
    immunities = []
    shapes = Counter()
    for record in records:
        fields, notes = parse_secondary(record)
        name = record["name"]
        if notes:
            raise SystemExit(f"Secondary parsing issue for {name}: {notes}")
        if "Gear" in fields:
            gears.append((name, fields["Gear"]))
        if "Immunities" in fields:
            raw = fields["Immunities"]
            immunities.append((name, raw))
            shapes["semicolon-separated" if ";" in raw else "no semicolon"] += 1
    lines = [
        "SRD GEAR / IMMUNITY SCHEMA REVIEW — NOT FOR IMPORT",
        f"Monsters: {len(records)}",
        f"Gear entries: {len(gears)}",
        f"Immunity entries: {len(immunities)}",
        f"Immunity formats: {dict(shapes)}",
        "",
        "ALL GEAR ENTRIES:",
    ]
    lines += [f"  {name}: {value}" for name, value in gears]
    lines += ["", "ALL IMMUNITY ENTRIES:"]
    lines += [f"  {name}: {value}" for name, value in immunities]
    lines += ["", "Do not infer damage vs condition from semicolon alone without review.",
              "No published or custom monsters were modified."]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Monsters: {len(records)}")
    print(f"Gear entries: {len(gears)}")
    print(f"Immunity entries: {len(immunities)}")
    print(f"Report: {OUTPUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
