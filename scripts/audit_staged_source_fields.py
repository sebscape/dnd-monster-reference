#!/usr/bin/env python3
"""Audit staged fields against source excerpts, emphasizing combat-critical data.

Diagnostic only; does not alter the staging catalog or published/custom data.
"""
import json
import re
from pathlib import Path
from parse_pilot_headers import parse as parse_header
from parse_pilot_secondary_stats import parse_secondary
from parse_pilot_features import parse as parse_features
from audit_immunity_classification import classify
from preview_hyphenation_normalization import CANDIDATE, LINE_JOIN, KEEP_HYPHEN

ROOT = Path("staging/srd-5.2.1")
OUT = ROOT / "staged-source-field-audit.txt"
SOURCE = ROOT / "monster-excerpts-cleaned.json"
STAGED = ROOT / "assembled-monsters-review.json"

def normalize_factory():
    candidates = CANDIDATE.findall((ROOT / "hyphenation-candidates-report.txt").read_text(encoding="utf-8"))
    if len(candidates) != 177:
        raise SystemExit(f"Expected 177 approved patterns; found {len(candidates)}")
    approved = {(left, right): proposed for left, right, proposed, _ in candidates
                if f"{left}-{right}" not in KEEP_HYPHEN}
    def normalize(text):
        def sub(m):
            left, right = m.groups()
            if f"{left}-{right}" in KEEP_HYPHEN:
                return left + "-" + right
            if (left, right) not in approved:
                raise ValueError(f"Unknown hyphenation: {left}-{right}")
            return approved[(left, right)]
        return LINE_JOIN.sub(sub, text)
    return normalize

def main():
    originals = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    staged = json.loads(STAGED.read_text(encoding="utf-8"))["monsters"]
    by_name = {m["name"]: m for m in staged}
    normalize = normalize_factory()
    issues = []
    checked = 0
    for original in originals:
        name = original["name"]
        if name not in by_name:
            continue
        record = dict(original, cleaned_excerpt=normalize(original["cleaned_excerpt"]))
        monster = by_name[name]
        header = parse_header(record)
        secondary, notes = parse_secondary(record)
        sections, preambles, warnings = parse_features(record)
        checked += 1
        for source_key, dest_key in [("ac","armor_class"),("hp","hit_points"),
                                      ("initiative","initiative_bonus"),("cr","challenge_rating"),
                                      ("pb","proficiency_bonus"),("speed","speed"),
                                      ("hit_dice","hit_dice")]:
            source_value = header[source_key]
            actual = monster.get(dest_key)
            if source_key in ("ac", "hp", "initiative", "pb") and source_value is not None:\n                source_value = int(source_value)\n            if source_value != actual:
                issues.append(f"{name}: {dest_key} mismatch: source {source_value!r}; staged {actual!r}")
        for source_key, dest_key in [("Skills","skills"),("Senses","senses"),
                                     ("Languages","languages"),("Vulnerabilities","damage_vulnerabilities"),
                                     ("Resistances","damage_resistances"),("Gear","gear")]:
            if secondary.get(source_key) != monster.get(dest_key):
                issues.append(f"{name}: {dest_key} differs from parsed source")
        damage, conditions, unknown = classify(secondary["Immunities"]) if "Immunities" in secondary else ([], [], [])
        if unknown or (", ".join(damage) or None) != monster.get("damage_immunities") or (", ".join(conditions) or None) != monster.get("condition_immunities"):
            issues.append(f"{name}: immunity mismatch")
        for source_key, dest_key in [("Traits","traits"),("Actions","actions"),
                                      ("Bonus Actions","bonus_actions"),("Reactions","reactions"),
                                      ("Legendary Actions","legendary_actions")]:
            if sections.get(source_key, []) != monster.get(dest_key, []):
                issues.append(f"{name}: {dest_key} feature text mismatch")
        if preambles.get("Legendary Actions") != monster.get("legendary_actions_intro"):
            issues.append(f"{name}: legendary introduction mismatch")
        if notes or warnings:
            issues.append(f"{name}: parser notes {notes} / {warnings}")
    lines = ["SRD STAGED SOURCE-FIELD AUDIT — NOT FOR PUBLICATION",
             f"Staged monsters inspected: {checked}",
             f"Field mismatches: {len(issues)}",\n             "Numeric source fields are converted to integers before comparison.", "",
             "MISMATCHES:", *(issues or ["none"]), "",
             "This checks staging against parsed source excerpts, not against PDF page images.",
             "Ability save interpretation, spellcasting presentation, and source typography require further review.",
             "No published or custom monsters were modified."]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Staged monsters inspected: {checked}")
    print(f"Field mismatches: {len(issues)}")
    print(f"Report: {OUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
