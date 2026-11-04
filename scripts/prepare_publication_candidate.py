#!/usr/bin/env python3
"""Prepare a review-only publication candidate, preserving four existing IDs.

Writes only staging/srd-5.2.1 files. Never edits public/data or browser storage.
"""
import json
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
STAGED = ROOT / "assembled-monsters-review.json"
PUBLISHED = Path("public/data/published-monsters.json")
CANDIDATE = ROOT / "publication-candidate-review.json"
REPORT = ROOT / "publication-candidate-review-report.txt"

def main():
    staged = json.loads(STAGED.read_text(encoding="utf-8"))
    published = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    monsters = staged["monsters"]
    seeds = published["monsters"]
    if len(monsters) != 330 or len(seeds) != 4:
        raise SystemExit("Expected 330 staged and 4 existing published monsters; no candidate written")
    by_name = {m["name"]: m for m in monsters}
    if len(by_name) != len(monsters):
        raise SystemExit("Duplicate staged names; no candidate written")
    old_ids = {m["name"]: m["id"] for m in seeds}
    if len(old_ids) != 4 or not all(name in by_name for name in old_ids):
        raise SystemExit("Published seed names mismatch; no candidate written")
    candidate = json.loads(json.dumps(staged))
    candidate["catalog_version"] = "CANDIDATE-REVIEW-ONLY"
    candidate["source"] = published["source"]
    for monster in candidate["monsters"]:
        if monster["name"] in old_ids:
            monster["id"] = old_ids[monster["name"]]
    ids = [m["id"] for m in candidate["monsters"]]
    if len(set(ids)) != 330:
        raise SystemExit("ID collision after preserving seed IDs; no candidate written")
    for name, old_id in old_ids.items():
        if next(m["id"] for m in candidate["monsters"] if m["name"] == name) != old_id:
            raise SystemExit("ID preservation failed for " + name)
    CANDIDATE.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "SRD PUBLICATION CANDIDATE — REVIEW ONLY, NOT PUBLISHED",
        f"Candidate records: {len(candidate['monsters'])}",
        f"Unique IDs: {len(set(ids))}",
        f"Original published IDs retained: {len(old_ids)}",
        f"Schema version: {candidate['schema_version']}",
        "Candidate file: " + str(CANDIDATE),
        "",
        "PRESERVED SEED IDS:",
        *(f"  {name}: {old_id}" for name, old_id in old_ids.items()),
        "",
        "PENDING BEFORE PUBLICATION:",
        "  Visual comparison of representative stat blocks against original SRD PDF",
        "  Verify all feature descriptions and spellcasting formatting",
        "  Browser testing with 330 monsters and existing custom monsters",
        "  Confirm attribution and schema migration",
        "",
        "No public/data files or browser custom monsters were modified.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Candidate records: {len(candidate['monsters'])}; original IDs preserved: {len(old_ids)}")
    print(f"Report: {REPORT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
