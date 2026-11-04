#!/usr/bin/env python3
"""Prepare and audit a final review-only SRD catalog, without publishing it."""
import json
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "publication-candidate-size-reviewed.json"
LIVE = Path("public/data/published-monsters.json")
OUTPUT = ROOT / "publication-candidate-final-review.json"
REPORT = ROOT / "final-candidate-readiness-report.txt"
FEATURES = ("traits", "actions", "bonus_actions", "reactions", "legendary_actions", "spellcasting")
REQUIRED = ("id", "name", "size", "type", "challenge_rating", "armor_class",
            "hit_points", "initiative_bonus", "abilities", "source",
            "timestamp_created", "timestamp_modified", "tags")
FIXED = {
    "Fire Elemental": ("Illumination", "30-foot"),
    "Nightmare": ("Illumination", "10-foot"),
    "Pit Fiend": ("Fear Aura", "20-foot"),
    "Vampire": ("Misty Escape", "Shape-Shift"),
}
def main():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    published = json.loads(LIVE.read_text(encoding="utf-8"))
    monsters = doc["monsters"]
    seeds = published["monsters"]
    issues = []
    names = [m.get("name") for m in monsters]
    ids = [m.get("id") for m in monsters]
    if len(monsters) != 330 or len(set(names)) != 330 or len(set(ids)) != 330:
        issues.append("Expected 330 monsters with unique names and IDs")
    if len(seeds) != 4:
        issues.append("Expected four published seed monsters")
    by_name = {m["name"]: m for m in monsters}
    for seed in seeds:
        if by_name.get(seed["name"], {}).get("id") != seed["id"]:
            issues.append("Seed ID not preserved: " + seed["name"])
    for m in monsters:
        for field in REQUIRED:
            if field not in m:
                issues.append(f"{m.get('name')}: missing {field}")
        if m.get("source", {}).get("type") != "official_srd":
            issues.append(f"{m.get('name')}: unexpected source type")
        for section in FEATURES:
            for feature in m.get(section, []):
                if not isinstance(feature.get("name"), str) or not isinstance(feature.get("description"), str):
                    issues.append(f"{m.get('name')}: malformed {section}")
        if m.get("legendary_actions") and not m.get("legendary_actions_intro"):
            issues.append(f"{m.get('name')}: legendary rules missing")
    if sum(m["size"] == "Medium or Small" for m in monsters) != 36:
        issues.append("Expected 36 restored alternative-size monsters")
    for name, (feature_name, expected_text) in FIXED.items():
        matches = [f for f in by_name.get(name, {}).get("traits", []) if f["name"] == feature_name]
        if len(matches) != 1 or expected_text not in matches[0]["description"]:
            issues.append(f"Missing text correction: {name}/{feature_name}")
    dragon = by_name.get("Young White Dragon", {})
    if dragon.get("saving_throws") != "Dex +3, Int +2, Wis +3":
        issues.append("Young White Dragon documented interpretation changed")
    if doc.get("schema_version") != "1.2.0":
        issues.append("Unexpected schema version")
    source_metadata = dict(doc.get("source", {}))
    if not source_metadata:
        issues.append("Missing top-level source attribution")
    if issues:
        REPORT.write_text("FINAL CANDIDATE NOT READY\n" + "\n".join(issues) + "\n", encoding="utf-8")
        print("Final candidate blocked; see " + str(REPORT))
        raise SystemExit(1)
    source_metadata["modifications"] = (
        "SRD 5.2.1 stat-block text extracted and reorganized into structured JSON; "
        "PDF line wraps and hyphenation normalized; non-stat-block headings removed; "
        "four text-wrap artifacts corrected; 36 alternative size descriptions restored. "
        "Young White Dragon Intelligence saving throw printed unsigned 2 on PDF printed "
        "page 340 and provisionally interpreted as +2."
    )
    doc["source"] = source_metadata
    doc["catalog_version"] = "FINAL-REVIEW-ONLY"
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "FINAL SRD CANDIDATE READINESS — REVIEW ONLY",
        f"Monsters: {len(monsters)}",
        f"Unique names: {len(set(names))}",
        f"Unique IDs: {len(set(ids))}",
        "Original published IDs preserved: 4",
        "Alternative-size descriptions restored: 36",
        "Targeted text corrections retained: 4",
        "Schema version: 1.2.0",
        "Structural readiness issues: 0",
        "Attribution modifications note: corrected",
        "Documented source ambiguity: Young White Dragon Int save +2 (PDF unsigned 2)",
        "",
        "PENDING: Independent visual comparison with original PDF pages.",
        "PENDING: Explicit user approval before replacing published catalog.",
        "This script did not alter published or custom monsters.",
        "Output: " + str(OUTPUT),
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
if __name__ == "__main__":
    main()
