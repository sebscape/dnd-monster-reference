#!/usr/bin/env python3
"""Create a corrected review-only candidate with four audited PDF wrap fixes.

Never modifies the original candidate, published catalog, or browser storage.
"""
import json
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SRC = ROOT / "publication-candidate-review.json"
DST = ROOT / "publication-candidate-text-reviewed.json"
REPORT = ROOT / "text-correction-review-report.txt"
FIXES = {
    ("Fire Elemental", "traits", "Illumination"): ("30- foot", "30-foot"),
    ("Nightmare", "traits", "Illumination"): ("10- foot", "10-foot"),
    ("Pit Fiend", "traits", "Fear Aura"): ("20- foot", "20-foot"),
    ("Vampire", "traits", "Misty Escape"): ("Shape- Shift", "Shape-Shift"),
}
def main():
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    if len(doc["monsters"]) != 330:
        raise SystemExit("Expected 330 monsters; no corrected file written")
    applied = []
    for monster in doc["monsters"]:
        for section in ("traits", "actions", "bonus_actions", "reactions", "legendary_actions", "spellcasting"):
            for feature in monster.get(section, []):
                key = (monster["name"], section, feature["name"])
                if key not in FIXES:
                    continue
                before, after = FIXES[key]
                if feature["description"].count(before) != 1:
                    raise SystemExit(f"Expected exactly one {before!r} in {key}; no corrected file written")
                feature["description"] = feature["description"].replace(before, after)
                applied.append((key, before, after))
    if len(applied) != len(FIXES):
        raise SystemExit("Not all four audited features found; no corrected file written")
    doc["catalog_version"] = "TEXT-CORRECTED-REVIEW-ONLY"
    DST.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "SRD TEXT CORRECTION REVIEW — NOT PUBLISHED",
        f"Candidate monsters: {len(doc['monsters'])}",
        f"Targeted replacements: {len(applied)}",
        "",
        "CHANGES:",
        *(f"  {key[0]} / {key[1]} / {key[2]}: {before!r} -> {after!r}" for key, before, after in applied),
        "",
        "Original candidate retained unchanged.",
        "Spellcasting text remains unchanged pending presentation review.",
        "No public/data or browser custom records modified.",
        "Output: " + str(DST),
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
if __name__ == "__main__":
    main()
