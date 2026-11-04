#!/usr/bin/env python3
"""Validate the staged SRD catalog and compare four existing seed records.

Review only. Does not modify either published or custom catalog.
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
STAGED = ROOT / "assembled-monsters-review.json"
PUBLISHED = Path("public/data/published-monsters.json")
OUT = ROOT / "staging-catalog-validation-report.txt"
FEATURES = ("traits", "actions", "bonus_actions", "reactions", "legendary_actions", "spellcasting")
REQUIRED = ("id", "name", "size", "type", "challenge_rating", "armor_class",
            "hit_points", "initiative_bonus", "abilities", "source",
            "timestamp_created", "timestamp_modified", "tags")
COMPARE = ("size", "type", "alignment", "challenge_rating", "proficiency_bonus",
           "armor_class", "armor_description", "hit_points", "hit_dice",
           "initiative_bonus", "speed", "abilities", "saving_throws", "skills",
           "damage_vulnerabilities", "damage_resistances", "damage_immunities",
           "condition_immunities", "senses", "languages", "gear",
           "legendary_actions_intro", *FEATURES)
def main():
    staged = json.loads(STAGED.read_text(encoding="utf-8"))["monsters"]
    seeds = json.loads(PUBLISHED.read_text(encoding="utf-8"))["monsters"]
    issues = []
    counts = Counter()
    seen_names, seen_ids = set(), set()
    for m in staged:
        name = m.get("name", "[unnamed]")
        for field in REQUIRED:
            if field not in m:
                issues.append(f"{name}: missing required field {field}")
        if name in seen_names: issues.append(f"Duplicate name: {name}")
        if m.get("id") in seen_ids: issues.append(f"Duplicate UUID: {m.get('id')}")
        seen_names.add(name)
        seen_ids.add(m.get("id"))
        if set(m.get("abilities", {})) != {"str","dex","con","int","wis","cha"}:
            issues.append(f"{name}: incomplete ability scores")
        if m.get("source", {}).get("type") != "official_srd":
            issues.append(f"{name}: unexpected source")
        for key in FEATURES:
            if key in m:
                if not isinstance(m[key], list) or any(
                    not isinstance(f, dict) or not isinstance(f.get("name"), str)
                    or not isinstance(f.get("description"), str) for f in m[key]):
                    issues.append(f"{name}: invalid {key}")
                else:
                    counts[key] += len(m[key])
        if m.get("legendary_actions") and not m.get("legendary_actions_intro"):
            issues.append(f"{name}: legendary actions without introductory rules")
    comparisons = []
    staged_by_name = {m["name"]: m for m in staged}
    for seed in seeds:
        name = seed["name"]
        if name not in staged_by_name:
            comparisons.append(f"{name}: MISSING FROM STAGING")
            continue
        current = staged_by_name[name]
        differences = [(key, seed.get(key), current.get(key)) for key in COMPARE
                       if seed.get(key) != current.get(key)]
        comparisons.append(f"=== {name}: {len(differences)} differences ===")
        for key, old, new in differences:
            comparisons.append(f"  {key}:")
            comparisons.append(f"    Published seed: {str(old)[:700]}")
            comparisons.append(f"    Staged source:  {str(new)[:700]}")
    lines = [
        "STAGING SRD CATALOG VALIDATION — NOT FOR PUBLICATION",
        f"Staged records: {len(staged)}",
        f"Existing published seed records: {len(seeds)}",
        f"Structural issues: {len(issues)}",
        f"Unique names: {len(seen_names)}",
        f"Unique UUIDs: {len(seen_ids)}",
        f"Feature counts: {dict(counts)}",
        "", "STRUCTURAL ISSUES:", *(issues or ["none"]),
        "", "EXISTING SEED COMPARISONS:", *comparisons,
        "", "This report does not verify accuracy against the SRD PDF.",
        "No published or custom monsters were modified.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Staged records: {len(staged)}")
    print(f"Structural issues: {len(issues)}")
    print(f"Report: {OUT}")
    print("No published or custom monsters were modified.")
if __name__ == "__main__":
    main()
