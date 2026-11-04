#!/usr/bin/env python3
"""Pilot extraction of named monster features, with ambiguity warnings.

Only staging diagnostic output. Never writes to the published monster catalog.
"""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
OUTPUT = ROOT / "pilot-feature-parsing-report.txt"
PILOTS = ["Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat",
          "Ancient Bronze Dragon", "Cloud Giant", "Ancient Copper Dragon",
          "Shrieker Fungus"]
SECTIONS = {"Traits", "Actions", "Bonus Actions", "Reactions", "Legendary Actions"}
# Feature name starts a paragraph, followed by a period and descriptive text.
FEATURE_START = re.compile(r"^([A-Z][A-Za-z0-9’'() /,+–-]{1,90}?)\.\s+(.+)$")
PREAMBLE = re.compile(r"^Legendary Action Uses:")

def parse(record):
    lines = record["cleaned_excerpt"].splitlines()
    cr = next((i for i, line in enumerate(lines) if re.match(r"^CR\s+", line.strip())), None)
    if cr is None:
        return {}, ["Missing CR boundary"]
    sections = {}
    warnings = []
    section = None
    current = None
    paragraph_start = True
    preambles = {}
    collecting_preamble = False
    for raw in lines[cr + 1:]:
        line = raw.strip()
        if line in SECTIONS:
            section = line
            sections.setdefault(section, [])
            current = None
            paragraph_start = True
            collecting_preamble = False
            continue
        if not section:
            continue
        if not line:
            paragraph_start = True
            continue
        if section == "Legendary Actions" and PREAMBLE.match(line):
            preambles[section] = line
            collecting_preamble = True
            paragraph_start = False
            continue
        if collecting_preamble:
            if paragraph_start:
                collecting_preamble = False
            else:
                preambles[section] += " " + line
                continue
        candidate = FEATURE_START.match(line) if paragraph_start else None
        if candidate and not PREAMBLE.match(line):
            name, description = candidate.groups()
            current = {"name": name, "description": description}
            sections[section].append(current)
        elif current:
            # Preserve words and punctuation, but do not silently dehyphenate.
            current["description"] += " " + line
        else:
            warnings.append(f"{section}: unassigned text: {line[:100]}")
        paragraph_start = False
    return sections, preambles, warnings

def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    by_name = {r["name"]: r for r in data["records"]}
    out = ["SRD PILOT FEATURE PARSING — UNVERIFIED / NOT FOR IMPORT",
           "Descriptions retain extraction hyphenation; inspect manually.", ""]
    for name in PILOTS:
        if name not in by_name:
            raise SystemExit(f"Missing pilot {name}")
        sections, preambles, warnings = parse(by_name[name])
        out.append(f"=== {name} ===")
        for section, features in sections.items():
            out.append(f"  {section} ({len(features)}):")
            if section in preambles:
                out.append(f"    Section rules: {preambles[section]}")
            for feature in features:
                out.append(f"    - {feature['name']}: {feature['description'][:180]}")
        out.append(f"  Warnings ({len(warnings)}):")
        out.extend(f"    ! {warning}" for warning in warnings[:30])
        if len(warnings) > 30:
            out.append(f"    ... {len(warnings) - 30} more")
        out.append("")
    out.append("No published or custom monsters were modified.")
    OUTPUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Pilot monsters: {len(PILOTS)}")
    print(f"Report: {OUTPUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
