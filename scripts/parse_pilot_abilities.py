#!/usr/bin/env python3
"""Parse six ability scores, modifiers, and saves in five SRD pilot excerpts.

Diagnostic only. Ambiguous rows are reported, never guessed or imported.
"""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
OUTPUT = ROOT / "pilot-ability-parsing-report.txt"
PILOTS = ["Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat"]
ABILITIES = ["Str", "Dex", "Con", "Int", "Wis", "Cha"]
ROW_START = re.compile(r"^(Str|Dex|Con|Int|Wis|Cha)\s+(\d+)\b(.*)$")
SIGNED = re.compile(r"[+-]\d+")
DASHES = str.maketrans({"−": "-", "–": "-", "—": "-"})

def parse_abilities(record):
    lines = [line.strip().translate(DASHES) for line in record["cleaned_excerpt"].splitlines()]
    result = {}
    issues = []
    for i, line in enumerate(lines):
        match = ROW_START.match(line)
        if not match:
            continue
        label, score_text, tail = match.groups()
        if label in result:
            issues.append(f"Duplicate ability: {label}")
            continue
        parts = SIGNED.findall(tail)
        j = i + 1
        while len(parts) < 2 and j < len(lines):
            following = lines[j]
            if ROW_START.match(following) or following == "" or following.startswith("CR "):
                break
            if re.fullmatch(r"(?:[+-]\d+)(?:\s+[+-]\d+)*", following):
                parts.extend(SIGNED.findall(following))
            elif re.fullmatch(r"\\d+", following):
                issues.append(f"{label}: unsigned standalone value {following!r} at line {j + 1}; possible lost sign; manual PDF review required")
                break
            else:
                break
            j += 1
        if len(parts) != 2:
            issues.append(f"{label}: expected modifier and save, found {parts}")
            continue
        score = int(score_text)
        modifier = int(parts[0])
        save = int(parts[1])
        expected_modifier = (score - 10) // 2
        if modifier != expected_modifier:
            issues.append(f"{label}: modifier {modifier:+d} differs from calculated {expected_modifier:+d}")
        result[label.lower()] = {"score": score, "modifier": modifier, "save": save}
    missing = [name for name in ABILITIES if name.lower() not in result]
    if missing:
        issues.append("Missing abilities: " + ", ".join(missing))
    return result, issues

def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = {item["name"]: item for item in data["records"]}
    report = ["SRD pilot ability parsing — UNVERIFIED / NOT FOR IMPORT", ""]
    total_issues = 0
    for name in PILOTS:
        if name not in records:
            raise SystemExit(f"Missing pilot: {name}")
        values, issues = parse_abilities(records[name])
        total_issues += len(issues)
        report.append(f"=== {name} ===")
        for ability in ABILITIES:
            value = values.get(ability.lower())
            if value:
                report.append(f"  {ability}: score {value['score']}, modifier {value['modifier']:+d}, save {value['save']:+d}")
            else:
                report.append(f"  {ability}: [UNPARSED]")
        report.append("  Issues: " + ("; ".join(issues) if issues else "none"))
        report.append("")
    report.append(f"Total flagged issues: {total_issues}")
    report.append("No published or custom monsters were modified.")
    OUTPUT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Pilot monsters: {len(PILOTS)}")
    print(f"Flagged issues: {total_issues}")
    print(f"Report: {OUTPUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
