#!/usr/bin/env python3
"""Verify that feature parsing retains all non-whitespace text after SRD section headings.

Staging audit only. Compares source section text to reconstructed parsed text,
including legendary-action preambles, without modifying either catalog.
"""
import json
import re
from pathlib import Path
from parse_pilot_features import parse, SECTIONS

ROOT = Path("staging/srd-5.2.1")
OUT = ROOT / "feature-text-preservation-audit.txt"
SOURCE = ROOT / "monster-excerpts-cleaned.json"

def canonical(text):
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()

def source_sections(record):
    lines = record["cleaned_excerpt"].splitlines()
    cr = next(i for i, line in enumerate(lines) if re.match(r"^CR\s+", line.strip()))
    chunks = {}
    section = None
    for raw in lines[cr + 1:]:
        line = raw.strip()
        if line in SECTIONS:
            section = line
            chunks.setdefault(section, [])
        elif section is not None and line:
            chunks[section].append(line)
    return {section: canonical(" ".join(parts)) for section, parts in chunks.items()}

def reconstructed_sections(sections, preambles):
    result = {}
    for section, features in sections.items():
        parts = []
        if section in preambles:
            parts.append(preambles[section])
        for feature in features:
            parts.append(feature["name"] + ". " + feature["description"])
        result[section] = canonical(" ".join(parts))
    return result

def main():
    records = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    if len(records) != 330:
        raise SystemExit(f"Expected 330 monsters; found {len(records)}")
    mismatches = []
    for record in records:
        parsed, preambles, warnings = parse(record)
        if warnings:
            mismatches.append((record["name"], "Parser warnings: " + "; ".join(warnings)))
        original = source_sections(record)
        rebuilt = reconstructed_sections(parsed, preambles)
        for section in sorted(set(original) | set(rebuilt)):
            before = original.get(section, "")
            after = rebuilt.get(section, "")
            if before != after:
                i = next((i for i, (a, b) in enumerate(zip(before, after)) if a != b),
                         min(len(before), len(after)))
                mismatches.append((record["name"], f"{section}: mismatch at character {i}\n"
                    f"  Source: {before[max(0,i-65):i+135]!r}\n"
                    f"  Parsed: {after[max(0,i-65):i+135]!r}"))
    lines = [
        "SRD FEATURE TEXT PRESERVATION AUDIT — STAGING ONLY",
        f"Monsters inspected: {len(records)}",
        f"Section mismatches: {len(mismatches)}",
        "",
        "MISMATCH DETAILS:",
    ]
    if not mismatches:
        lines.append("  none")
    else:
        for name, issue in mismatches:
            lines.append(f"=== {name} ===\n{issue}")
    lines += ["", "This checks text preservation, not correctness against the PDF.",
              "No published or custom monsters were modified."]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Monsters inspected: {len(records)}")
    print(f"Section mismatches: {len(mismatches)}")
    print(f"Report: {OUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
