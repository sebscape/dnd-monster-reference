#!/usr/bin/env python3
"""Inspect Young White Dragon ability rows without changing source data."""
import json
from pathlib import Path

root = Path("staging/srd-5.2.1")
data = json.loads((root / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))
record = next((r for r in data["records"] if r["name"] == "Young White Dragon"), None)
if record is None:
    raise SystemExit("Young White Dragon not found")
lines = record["cleaned_excerpt"].splitlines()
out = ["Young White Dragon — raw ability area (review only)", ""]
for index, line in enumerate(lines[:48], 1):
    out.append(f"{index:02d}: {line!r}")
out += ["", "No published or custom monsters were modified."]
path = root / "young-white-dragon-ability-review.txt"
path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"Report: {path}")
print("No published or custom monsters were modified.")
