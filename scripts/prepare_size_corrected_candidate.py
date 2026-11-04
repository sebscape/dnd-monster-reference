#!/usr/bin/env python3
"""Restore 36 alternative SRD size descriptors in a new review-only catalog."""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
CANDIDATE = ROOT / "publication-candidate-text-reviewed.json"
OUTPUT = ROOT / "publication-candidate-size-reviewed.json"
REPORT = ROOT / "size-correction-review-report.txt"
PATTERN = re.compile(r"^(Tiny|Small|Medium|Large|Huge|Gargantuan) or (Tiny|Small|Medium|Large|Huge|Gargantuan)\s+")

def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    catalog = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    monsters = catalog["monsters"]
    if len(source) != 330 or len(monsters) != 330:
        raise SystemExit("Expected 330 records in both inputs")
    original_sizes = {}
    for record in source:
        lines = [s.strip() for s in record["cleaned_excerpt"].splitlines() if s.strip()]
        if record["name"] not in lines:
            raise SystemExit("Missing source title: " + record["name"])
        descriptor = lines[lines.index(record["name"]) + 1]
        match = PATTERN.match(descriptor)
        if match:
            original_sizes[record["name"]] = match.group(1) + " or " + match.group(2)
    if len(original_sizes) != 36:
        raise SystemExit(f"Expected 36 multiple-size monsters, found {len(original_sizes)}")
    corrections = []
    for monster in monsters:
        name = monster["name"]
        if name not in original_sizes:
            continue
        expected = original_sizes[name]
        if monster["size"] != expected.split(" or ")[0]:
            raise SystemExit(f"Unexpected current size for {name}: {monster['size']!r}")
        corrections.append((name, monster["size"], expected))
    if len(corrections) != 36:
        raise SystemExit(f"Expected 36 candidate corrections, found {len(corrections)}")
    for monster in monsters:
        if monster["name"] in original_sizes:
            monster["size"] = original_sizes[monster["name"]]
    catalog["catalog_version"] = "SIZE-CORRECTED-REVIEW-ONLY"
    OUTPUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "SRD SIZE CORRECTION — REVIEW ONLY, NOT PUBLISHED",
        f"Candidate records: {len(monsters)}",
        f"Alternative-size descriptions restored: {len(corrections)}",
        "All restored values: Medium or Small",
        "",
        "CORRECTED MONSTERS:",
        *(f"  {name}: {before} -> {after}" for name, before, after in corrections),
        "",
        "Four earlier text-artifact corrections retained.",
        "No schema changes, published files, or browser custom monsters modified.",
        "Output: " + str(OUTPUT),
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Corrected size descriptors: {len(corrections)}")
    print("Report: " + str(REPORT))
    print("Published and custom monsters unchanged.")

if __name__ == "__main__":
    main()
