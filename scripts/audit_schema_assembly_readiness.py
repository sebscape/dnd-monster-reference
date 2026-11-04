#!/usr/bin/env python3
"""Audit SRD fields against the Monster v1.1 schema before record assembly.

Diagnostic only: does not produce importable JSON or modify catalog files.
"""
import json
import re
from collections import Counter
from pathlib import Path
from parse_pilot_headers import parse as parse_header
from parse_pilot_abilities import parse_abilities
from parse_pilot_secondary_stats import parse_secondary
from parse_pilot_features import parse as parse_features

ROOT = Path("staging/srd-5.2.1")
OUT = ROOT / "schema-assembly-readiness-audit.txt"
FIELDS = ("name", "size", "ac", "hp", "initiative", "cr", "pb", "speed")
DESCRIPTOR = re.compile(r"^(Gargantuan|Huge|Large|Medium|Small|Tiny)(?: or (?:Small|Medium))?\s+(.+)$")
def main():
    records = json.loads((ROOT / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))["records"]
    if len(records) != 330:
        raise SystemExit(f"Expected 330 monsters; found {len(records)}")
    missing = []
    unusual = []
    descriptor_counts = Counter()
    for record in records:
        name = record["name"]
        header = parse_header(record)
        abilities, ability_issues = parse_abilities(record)
        secondary, secondary_issues = parse_secondary(record)
        sections, preambles, feature_issues = parse_features(record)
        for field in FIELDS:
            if header.get(field) is None:
                missing.append(f"{name}: missing {field}")
        descriptor = header["descriptor"]
        match = DESCRIPTOR.match(descriptor)
        if not match:
            unusual.append(f"{name}: unparsed size/type descriptor: {descriptor!r}")
        else:
            remainder = match.group(2)
            descriptor_counts[remainder] += 1
            if "," not in remainder:
                unusual.append(f"{name}: descriptor without comma/alignment: {descriptor!r}")
        if ability_issues:
            unusual.append(f"{name}: abilities: {'; '.join(ability_issues)}")
        if len(abilities) != 6:
            unusual.append(f"{name}: {len(abilities)} of six abilities parsed")
        if secondary_issues or feature_issues:
            unusual.append(f"{name}: secondary/features: {secondary_issues}; {feature_issues}")
        if "Immunities" in secondary and ";" not in secondary["Immunities"]:
            # Not an error: this may be damage-only or condition-only.
            pass
    lines = [
        "SRD MONSTER SCHEMA ASSEMBLY READINESS — DIAGNOSTIC ONLY",
        f"Monsters examined: {len(records)}",
        f"Missing required header fields: {len(missing)}",
        f"Unusual/ambiguous records: {len(unusual)}",
        "",
        "REQUIRED FIELD ISSUES:",
        *(missing or ["none"]),
        "",
        "AMBIGUITIES:",
        *(unusual or ["none"]),
        "",
        "DESCRIPTOR VARIANTS (size removed; exact source text):",
    ]
    for descriptor, count in descriptor_counts.most_common():
        lines.append(f"  {count:3} | {descriptor}")
    lines += [
        "",
        "KNOWN SCHEMA GAPS TO DESIGN BEFORE IMPORT:",
        "- Monster v1.1 has no dedicated legendary-action usage rules field.",
        "- Monster v1.1 has no dedicated Gear field.",
        "- Saving throws require converting six per-ability values into a string.",
        "- Immunities must be split into damage and condition categories safely.",
        "- Spellcasting must remain available in the correct action/trait section.",
        "- Young White Dragon Int save is ambiguous in source; do not infer silently.",
        "- Stable official monster IDs, timestamps, and source attribution need a policy.",
        "",
        "No published or custom monsters were modified.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Monsters: {len(records)}")
    print(f"Missing required header fields: {len(missing)}")
    print(f"Unusual/ambiguous records: {len(unusual)}")
    print(f"Report: {OUT}")
    print("No published or custom monsters were modified.")
if __name__ == "__main__":
    main()
