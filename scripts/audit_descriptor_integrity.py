#!/usr/bin/env python3
"""Read-only audit of size/type/alignment source descriptors for all SRD monsters."""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
CANDIDATE = ROOT / "publication-candidate-size-reviewed.json"
OUT = ROOT / "descriptor-integrity-audit.txt"
SIZE = re.compile(r"^(Tiny|Small|Medium|Large|Huge|Gargantuan)(?: or (Tiny|Small|Medium|Large|Huge|Gargantuan))?\s+")
ALIGNMENTS = (
    "Lawful Good", "Neutral Good", "Chaotic Good",
    "Lawful Neutral", "Neutral", "Chaotic Neutral",
    "Lawful Evil", "Neutral Evil", "Chaotic Evil",
    "Unaligned", "Any Alignment",
)
def main():
    originals = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    monsters = json.loads(CANDIDATE.read_text(encoding="utf-8"))["monsters"]
    if len(originals) != 330 or len(monsters) != 330:
        raise SystemExit("Expected 330 source and candidate records")
    by_name = {m["name"]: m for m in monsters}
    if len(by_name) != 330:
        raise SystemExit("Duplicate candidate names")
    issues, ambiguous = [], []
    for record in originals:
        name = record["name"]
        if name not in by_name:
            issues.append(f"{name}: missing from candidate")
            continue
        lines = [line.strip() for line in record["cleaned_excerpt"].splitlines() if line.strip()]
        if name not in lines or lines.index(name) + 1 >= len(lines):
            issues.append(f"{name}: missing descriptor after name")
            continue
        descriptor = lines[lines.index(name) + 1]
        match = SIZE.match(descriptor)
        if not match:
            issues.append(f"{name}: unrecognized size descriptor {descriptor!r}")
            continue
        first, second = match.groups()
        expected_size = first + (" or " + second if second else "")
        rest = descriptor[match.end():]
        if ", " not in rest:
            ambiguous.append(f"{name}: descriptor has no type/alignment separator: {descriptor!r}")
            continue
        expected_type, expected_alignment = rest.rsplit(", ", 1)
        actual = by_name[name]
        for key, expected in (
            ("size", expected_size),
            ("type", expected_type),
            ("alignment", expected_alignment),
        ):
            if actual.get(key) != expected:
                issues.append(f"{name}: {key}: source {expected!r}; candidate {actual.get(key)!r}")
        if expected_alignment not in ALIGNMENTS:
            ambiguous.append(f"{name}: unusual alignment {expected_alignment!r}")
    lines = [
        "SRD 5.2.1 DESCRIPTOR INTEGRITY AUDIT — REVIEW ONLY",
        f"Source records: {len(originals)}",
        f"Candidate monsters: {len(monsters)}",
        f"Size/type/alignment mismatches: {len(issues)}",
        f"Unusual or unparsed descriptors: {len(ambiguous)}",
        "",
        "MISMATCHES:", *(issues or ["none"]),
        "", "UNUSUAL/UNPARSED:", *(ambiguous or ["none"]),
        "", "Compares candidate against extracted PDF text, not visual PDF pages.",
        "No catalog or custom monster data was modified.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:5]))
    print("Report: " + str(OUT))
if __name__ == "__main__":
    main()
