#!/usr/bin/env python3
"""Audit parsed feature boundaries across all staged SRD monsters.

Diagnostic only; does not modify the source excerpts or either monster catalog.
"""
import json
import re
from collections import Counter
from pathlib import Path

from parse_pilot_features import parse

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
OUTPUT = ROOT / "all-feature-boundaries-audit.txt"
EXPECTED_SECTIONS = ("Traits", "Actions", "Bonus Actions", "Reactions", "Legendary Actions")

def main():
    records = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    if len(records) != 330:
        raise SystemExit(f"Expected 330 monsters, got {len(records)}")
    totals = Counter()
    warnings_by_monster = []
    anomalies = []
    for record in records:
        name = record["name"]
        sections, preambles, warnings = parse(record)
        for section, features in sections.items():
            totals[f"sections:{section}"] += 1
            totals[f"features:{section}"] += len(features)
            for feature in features:
                if not feature["description"].strip():
                    anomalies.append(f"{name}: empty description in {section}: {feature['name']}")
                if len(feature["name"]) > 75:
                    anomalies.append(f"{name}: long feature name in {section}: {feature['name']}")
        if "Legendary Actions" in sections and "Legendary Actions" not in preambles:
            anomalies.append(f"{name}: legendary actions lack preserved introductory rules")
        if warnings:
            warnings_by_monster.append((name, warnings))
        if not sections:
            anomalies.append(f"{name}: no feature sections")
    lines = [
        "ALL 330 SRD MONSTERS — FEATURE BOUNDARY AUDIT (NOT FOR IMPORT)",
        f"Monsters: {len(records)}",
        f"Monsters with parser warnings: {len(warnings_by_monster)}",
        f"Structural anomalies: {len(anomalies)}",
        "",
        "SECTION COUNTS:",
    ]
    for section in EXPECTED_SECTIONS:
        lines.append(f"  {section}: {totals[f'sections:{section}']} monsters; {totals[f'features:{section}']} named features")
    lines += ["", "PARSER WARNINGS:"]
    if not warnings_by_monster:
        lines.append("  none")
    for name, warnings in warnings_by_monster:
        lines.append(f"=== {name} ({len(warnings)}) ===")
        lines.extend(f"  {warning}" for warning in warnings[:15])
        if len(warnings) > 15:
            lines.append(f"  ... {len(warnings)-15} more")
    lines += ["", "STRUCTURAL ANOMALIES:"]
    lines.extend(f"  {item}" for item in anomalies or ["  none"])
    lines += ["", "No published or custom monsters were modified."]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Monsters: {len(records)}")
    print(f"Monsters with parser warnings: {len(warnings_by_monster)}")
    print(f"Structural anomalies: {len(anomalies)}")
    print(f"Report: {OUTPUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
