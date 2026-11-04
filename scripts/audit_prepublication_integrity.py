#!/usr/bin/env python3
"""Final prepublication integrity gate for staged SRD monsters.

Read-only. Verifies catalog identity, structural consistency, provenance,
and stable IDs required for existing derived_from references.
"""
import json
import uuid
from collections import Counter
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
STAGED = ROOT / "assembled-monsters-review.json"
SOURCE = ROOT / "monster-excerpts-cleaned.json"
PUBLISHED = Path("public/data/published-monsters.json")
OUT = ROOT / "prepublication-integrity-audit.txt"
SECTIONS = ("traits", "actions", "bonus_actions", "reactions", "legendary_actions", "spellcasting")
NAMESPACE = uuid.UUID("df7a48e0-f2bf-4b32-b6f7-612accd63920")

def main():
    staged_doc = json.loads(STAGED.read_text(encoding="utf-8"))
    published_doc = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    source_doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    staged = staged_doc["monsters"]
    seeds = published_doc["monsters"]
    source = source_doc["records"]
    errors = []
    warnings = []
    names = [m["name"] for m in staged]
    source_names = [r["name"] for r in source]
    ids = [m["id"] for m in staged]
    if len(staged) != 330: errors.append(f"Expected 330 staged monsters; found {len(staged)}")
    if len(source) != 330: errors.append(f"Expected 330 source excerpts; found {len(source)}")
    if len(set(names)) != len(names): errors.append("Duplicate staged monster names")
    if len(set(ids)) != len(ids): errors.append("Duplicate staged monster IDs")
    missing = sorted(set(source_names)-set(names))
    unexpected = sorted(set(names)-set(source_names))
    if missing: errors.append("Missing source names: " + repr(missing))
    if unexpected: errors.append("Unexpected staged names: " + repr(unexpected))
    for m in staged:
        name = m["name"]
        expected_id = str(uuid.uuid5(NAMESPACE, "srd-5.2.1:" + name))
        if m["id"] != expected_id:
            errors.append(f"{name}: unexpected staged UUID")
        if m.get("source", {}).get("type") != "official_srd":
            errors.append(f"{name}: unexpected source type")
        for key in SECTIONS:
            for i, feature in enumerate(m.get(key, [])):
                if not feature.get("name", "").strip() or not feature.get("description", "").strip():
                    errors.append(f"{name}: empty feature in {key}[{i}]")
        if m.get("legendary_actions") and not m.get("legendary_actions_intro"):
            errors.append(f"{name}: missing legendary action usage text")
    seed_ids = {m["name"]:m["id"] for m in seeds}
    if len(seed_ids) != 4:
        errors.append(f"Expected four existing published seed monsters; found {len(seed_ids)}")
    staged_by_name = {m["name"]:m for m in staged}
    collisions = []
    for name, old_id in seed_ids.items():
        if name not in staged_by_name:
            errors.append(f"Published seed absent from staged catalog: {name}")
        else:
            collisions.append((name, old_id, staged_by_name[name]["id"]))
            if old_id == staged_by_name[name]["id"]:
                warnings.append(f"{name}: staged ID already equals existing published ID")
    if not any(m["name"] == "Young White Dragon" and m.get("saving_throws", "").find("Int +2") >= 0 for m in staged):
        errors.append("Young White Dragon Int +2 editorial interpretation absent")
    lines = [
        "SRD PREPUBLICATION INTEGRITY AUDIT — READ ONLY",
        f"Source excerpts: {len(source)}",
        f"Staged monsters: {len(staged)}",
        f"Published seed monsters: {len(seeds)}",
        f"Distinct staged names: {len(set(names))}",
        f"Distinct staged IDs: {len(set(ids))}",
        f"Blocking errors: {len(errors)}",
        f"Advisory notes: {len(warnings)}",
        "", "BLOCKING ERRORS:", *(errors or ["none"]),
        "", "SEED ID MIGRATION REQUIREMENTS:",
    ]
    for name, old_id, new_id in collisions:
        lines.extend([
            f"  {name}",
            f"    KEEP existing published ID: {old_id}",
            f"    DO NOT publish generated staged ID: {new_id}",
        ])
    lines.extend([
        "",
        "SOURCE ANOMALY:",
        "Young White Dragon Int save printed unsigned 2 on SRD 5.2.1 p. 340;",
        "staging interprets it as +2. This remains an editorial interpretation.",
        "",
        "ADVISORY NOTES:", *(warnings or ["none"]),
        "",
        "This does not establish verbatim PDF accuracy or UI performance.",
        "Do not publish before preserving all four seed IDs and completing PDF spot checks.",
        "No staged, published, or custom monster records were modified.",
    ])
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Source excerpts: {len(source)}; staged: {len(staged)}")
    print(f"Blocking errors: {len(errors)}")
    print(f"Report: {OUT}")
    print("No staged, published, or custom monster records were modified.")

if __name__ == "__main__":
    main()
