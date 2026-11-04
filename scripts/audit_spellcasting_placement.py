#!/usr/bin/env python3
"""Audit spellcasting features in the review-only SRD catalog.

Does not change any published, staged, or custom monster records.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
CATALOG = ROOT / "assembled-monsters-review.json"
REPORT = ROOT / "spellcasting-placement-audit.txt"
SECTIONS = ("traits", "actions", "bonus_actions", "reactions", "legendary_actions")
SPELL = re.compile(r"\bspellcasting\b", re.IGNORECASE)
SPELL_TERMS = re.compile(r"\b(?:at will|spell slot|spell slots|level \d+ spell|cantrip|spell save DC|spell attack)\b", re.IGNORECASE)

def main():
    monsters = json.loads(CATALOG.read_text(encoding="utf-8"))["monsters"]
    matches = []
    counts = Counter()
    issues = []
    for monster in monsters:
        name = monster["name"]
        found = []
        for section in SECTIONS:
            for index, feature in enumerate(monster.get(section, [])):
                title = feature["name"]
                description = feature["description"]
                if SPELL.search(title) or SPELL.search(description) or SPELL_TERMS.search(description):
                    counts[section] += 1
                    found.append((section, index, title, description))
                    if not description.strip():
                        issues.append(f"{name} / {section} / {title}: empty description")
        if found:
            matches.append((name, found))
        for feature in monster.get("spellcasting", []):
            issues.append(f"{name}: separate spellcasting feature present; inspect for duplicated or displaced source text")
    lines = [
        "SRD SPELLCASTING FEATURE PLACEMENT — REVIEW ONLY",
        f"Monsters inspected: {len(monsters)}",
        f"Monsters with spellcasting-related text: {len(matches)}",
        f"Matched feature occurrences: {sum(counts.values())}",
        "Matches by original feature section: " + repr(dict(counts)),
        f"Automatic structural issues: {len(issues)}",
        "",
        "ISSUES:", *(issues or ["none"]),
        "",
        "SPELLCASTING-RELATED FEATURES (source section and order):",
    ]
    for name, features in matches:
        lines.append(f"=== {name} ===")
        for section, index, title, description in features:
            lines.append(f"  {section}[{index}] {title}")
            lines.append(f"    {description[:300]}")
    lines.extend([
        "",
        "This is a keyword inventory, not an assertion that all spellcasting is correct.",
        "Source sections and feature order are preserved in the staged catalog.",
        "Compare selected entries with the original PDF before publication.",
        "No published, staged, or custom monsters were modified.",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Monsters inspected: {len(monsters)}")
    print(f"Monsters with spellcasting-related text: {len(matches)}")
    print(f"Automatic structural issues: {len(issues)}")
    print(f"Report: {REPORT}")
    print("No published, staged, or custom monsters were modified.")

if __name__ == "__main__":
    main()
