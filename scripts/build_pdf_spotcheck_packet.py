#!/usr/bin/env python3
"""Create a source-vs-candidate spot-check packet for manual PDF verification.

Uses already extracted source excerpts, not independent visual PDF verification.
Does not modify any catalog.
"""
import json
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
CANDIDATE = ROOT / "publication-candidate-text-reviewed.json"
OUTPUT = ROOT / "pdf-spotcheck-review-packet.txt"
NAMES = (
    "Aboleth", "Giant Rat", "Goblin Minion", "Skeleton", "Zombie",
    "Adult Black Dragon", "Ancient Bronze Dragon", "Cloud Giant",
    "Shrieker Fungus", "Fire Elemental", "Pit Fiend", "Vampire",
    "Young White Dragon",
)
SECTIONS = ("traits", "actions", "bonus_actions", "reactions", "legendary_actions", "spellcasting")

def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))["monsters"]
    originals = {m["name"]: m for m in source}
    staged = {m["name"]: m for m in candidate}
    if len(source) != 330 or len(candidate) != 330:
        raise SystemExit("Expected 330 source and 330 candidate monsters")
    missing = [name for name in NAMES if name not in originals or name not in staged]
    if missing:
        raise SystemExit("Missing spot-check monsters: " + ", ".join(missing))
    lines = [
        "SRD 5.2.1 PDF SPOT-CHECK PACKET — MANUAL REVIEW REQUIRED",
        "Official PDF: https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf",
        f"Source records: {len(source)}; candidate records: {len(candidate)}",
        f"Representative sample: {len(NAMES)}",
        "IMPORTANT: extracted source text is not independent visual PDF verification.",
        "For each monster locate its printed stat block in the original PDF and compare",
        "AC, HP, initiative, CR, PB, six abilities and saves, immunities,",
        "all action names, spell lists, and legendary usage rules.",
        "Documented ambiguity: Young White Dragon Intelligence save printed unsigned 2",
        "on PDF printed page 340; candidate provisionally interprets it as +2.",
        "",
    ]
    for name in NAMES:
        original, monster = originals[name], staged[name]
        lines += ["=" * 78, "MONSTER: " + name, "-" * 78, "CANDIDATE STAT FIELDS:"]
        for key in ("size", "type", "alignment", "armor_class", "armor_description",
                    "hit_points", "hit_dice", "initiative_bonus", "speed",
                    "challenge_rating", "proficiency_bonus", "abilities",
                    "saving_throws", "skills", "damage_vulnerabilities",
                    "damage_resistances", "damage_immunities", "condition_immunities",
                    "senses", "languages", "gear", "legendary_actions_intro"):
            if key in monster:
                lines.append(f"  {key}: {monster[key]}")
        for section in SECTIONS:
            features = monster.get(section, [])
            if features:
                lines += ["", f"CANDIDATE {section.upper()} ({len(features)}):"]
                lines += [f"  {f['name']}: {f['description']}" for f in features]
        lines += ["", "EXTRACTED ORIGINAL SRD TEXT (UNVERIFIED AGAINST PDF IMAGE):",
                  original["cleaned_excerpt"], "", "MANUAL PDF CHECK: [ ] PASS  [ ] REVIEW", ""]
    lines += [
        "End of spot-check packet.",
        "No public/data, candidate, or browser custom monster records were modified.",
    ]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Spot-check packet: {len(NAMES)} monsters, {len(lines)} lines")
    print("Output: " + str(OUTPUT))
    print("No catalog files were modified.")

if __name__ == "__main__":
    main()
