#!/usr/bin/env python3
"""Read-only candidate quality scan: suspicious PDF artifacts and spellcasting layout."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "publication-candidate-review.json"
OUT = ROOT / "candidate-text-quality-audit.txt"
FEATURES = ("traits", "actions", "bonus_actions", "reactions", "legendary_actions", "spellcasting")
SPELL = re.compile(r"\b(?:Spellcasting|At Will:|[1-9]/Day(?: Each)?:)\b", re.I)
ARTIFACTS = [
    ("line break hyphen", re.compile(r"\w-\s+\w")),
    ("multiple spaces", re.compile(r" {2,}")),
    ("control characters", re.compile(r"[\x00-\x08\x0b-\x1f]")),
    ("possible next-section heading", re.compile(r"\b(?:Crawling Claw|Mages|Priests|Guards|Animated Objects)\s*$")),
    ("unrejoined word", re.compile(r"\b(?:crea ture|suc cess|dam age|abil ity)\b", re.I)),
]
def main():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    monsters = doc["monsters"]
    flags = []
    spellcasting = []
    counts = Counter()
    for m in monsters:
        for section in FEATURES:
            for feature in m.get(section, []):
                name, description = feature["name"], feature["description"]
                label = f"{m['name']} / {section} / {name}"
                counts[section] += 1
                if "spellcasting" in name.lower() or SPELL.search(description):
                    spellcasting.append(label + ": " + description[:240])
                for kind, pattern in ARTIFACTS:
                    if pattern.search(description):
                        flags.append(f"{kind}: {label}: {description[:240]}")
                if "\n" in description:
                    flags.append(f"embedded newline: {label}")
        if m.get("armor_description"):
            counts["armor_descriptions"] += 1
    lines = [
        "CANDIDATE TEXT QUALITY AUDIT — REVIEW ONLY",
        f"Monsters: {len(monsters)}",
        f"Feature counts: {dict(counts)}",
        f"Spellcasting-related feature occurrences: {len(spellcasting)}",
        f"Potential text artifacts: {len(flags)}",
        "",
        "POTENTIAL TEXT ARTIFACTS (REVIEW MANUALLY):",
        *(flags or ["none"]),
        "",
        "SPELLCASTING PRESENTATION SAMPLE (FIRST 40):",
        *(spellcasting[:40] or ["none"]),
        "",
        "This is a heuristic scan, not proof of source transcription accuracy.",
        "No published, candidate, or custom monster records were modified.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Monsters: {len(monsters)}; potential text artifacts: {len(flags)}")
    print(f"Spellcasting-related occurrences: {len(spellcasting)}")
    print(f"Report: {OUT}")
if __name__ == "__main__":
    main()
