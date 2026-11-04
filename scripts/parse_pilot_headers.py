#!/usr/bin/env python3
"""Pilot parser for SRD stat-block headers. Diagnostic output only."""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
OUTPUT = ROOT / "pilot-header-parsing-report.txt"
PILOTS = ["Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat"]
DASHES = str.maketrans({"−": "-", "–": "-", "—": "-"})

def match(pattern, text):
    result = re.search(pattern, text, re.MULTILINE)
    return result.group(1).strip() if result else None

def parse(record):
    text = record["cleaned_excerpt"].translate(DASHES)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    descriptor = lines[1] if len(lines) > 1 else ""
    size = match(r"^(Gargantuan|Huge|Large|Medium|Small|Tiny)(?: or (?:Small|Medium))?\s+", descriptor)
    ac = match(r"^AC\s+(\d+)", text)
    hp = match(r"^HP\s+(\d+)", text)
    hit_dice = match(r"^HP\s+\d+\s+\(([^)]+)\)", text)
    initiative = match(r"^Initiative\s+([+-]?\d+)", text)
    speed = match(r"^Speed\s+(.+)$", text)
    cr = match(r"^CR\s+(\d+/\d+|\d+)", text)
    pb = match(r"^CR\s+[^\n]*?PB\s+([+]?[0-9]+)", text)
    return {
        "name": record["name"], "descriptor": descriptor, "size": size,
        "ac": ac, "hp": hp, "hit_dice": hit_dice,
        "initiative": initiative, "speed": speed, "cr": cr, "pb": pb,
    }

def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = {record["name"]: record for record in data["records"]}
    lines = [
        "SRD 5.2.1 pilot header parsing — UNVERIFIED / NOT FOR IMPORT",
        "Five pilot monsters; diagnostic only.",
        "",
    ]
    for name in PILOTS:
        if name not in records:
            raise SystemExit(f"Missing pilot monster: {name}")
        parsed = parse(records[name])
        lines.append(name)
        for field, value in parsed.items():
            if field != "name":
                lines.append(f"  {field}: {value if value is not None else '[MISSING]'}")
        lines.append("")
    lines.append("No published or custom monsters were modified.")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Pilot monsters: {len(PILOTS)}")
    print(f"Report: {OUTPUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
