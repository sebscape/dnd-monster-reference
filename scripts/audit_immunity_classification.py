#!/usr/bin/env python3
"""Classify SRD immunity entries with explicit damage/condition vocabularies.

Diagnostic only. Retains conditional qualifications verbatim; reports unknown
tokens rather than guessing. No catalog files are changed.
"""
import json
from collections import Counter
from pathlib import Path
from parse_pilot_secondary_stats import parse_secondary

ROOT = Path("staging/srd-5.2.1")
OUT = ROOT / "immunity-classification-audit.txt"
DAMAGE = set("Acid Bludgeoning Cold Fire Force Lightning Necrotic Piercing Poison Psychic Radiant Slashing Thunder".split())
CONDITIONS = set("Blinded Charmed Deafened Exhaustion Frightened Grappled Incapacitated Invisible Paralyzed Petrified Poisoned Prone Restrained Stunned Unconscious".split())
def classify(value):
    damage, conditions, unknown = [], [], []
    for item in value.replace(";", ",").split(","):
        item = item.strip()
        root = item.split(" (", 1)[0]
        if root in DAMAGE:
            damage.append(item)
        elif root in CONDITIONS:
            conditions.append(item)
        else:
            unknown.append(item)
    return damage, conditions, unknown

def main():
    records = json.loads((ROOT / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))["records"]
    if len(records) != 330:
        raise SystemExit(f"Expected 330 monsters, got {len(records)}")
    counts = Counter()
    unknowns, qualified, mixed, damage_only, condition_only = [], [], [], [], []
    for record in records:
        fields, notes = parse_secondary(record)
        if notes:
            raise SystemExit(f"Secondary parser warning: {record['name']}: {notes}")
        raw = fields.get("Immunities")
        if raw is None:
            continue
        counts["entries"] += 1
        dmg, cond, other = classify(raw)
        if dmg and cond:
            mixed.append(record["name"])
        elif dmg:
            damage_only.append(record["name"])
        elif cond:
            condition_only.append(record["name"])
        if other:
            unknowns.append(f"{record['name']}: {other!r} | source: {raw}")
        for item in dmg + cond:
            if " (" in item:
                qualified.append(f"{record['name']}: {item}")
        # Lossless, order-independent token audit.
        originals = sorted(s.strip() for s in raw.replace(";", ",").split(","))
        rebuilt = sorted(dmg + cond + other)
        if originals != rebuilt:
            unknowns.append(f"{record['name']}: token preservation failure")
    lines = [
        "SRD IMMUNITY CLASSIFICATION — REVIEW ONLY",
        f"Monsters: {len(records)}",
        f"Immunity entries: {counts['entries']}",
        f"Mixed damage and condition: {len(mixed)}",
        f"Damage only: {len(damage_only)}",
        f"Condition only: {len(condition_only)}",
        f"Unknown or unpreserved tokens: {len(unknowns)}",
        f"Qualified tokens (verbatim): {len(qualified)}",
        "",
        "QUALIFIED TOKENS:",
        *(qualified or ["none"]),
        "",
        "UNKNOWN TOKENS:",
        *(unknowns or ["none"]),
        "",
        "CONDITION-ONLY MONSTERS:",
        *(condition_only or ["none"]),
        "",
        "No published or custom monsters were modified.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Immunity entries: {counts['entries']}")
    print(f"Mixed: {len(mixed)}; damage only: {len(damage_only)}; condition only: {len(condition_only)}")
    print(f"Unknown/unpreserved tokens: {len(unknowns)}")
    print(f"Report: {OUT}")
    print("No published or custom monsters were modified.")
if __name__ == "__main__":
    main()
