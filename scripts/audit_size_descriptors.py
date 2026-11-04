#!/usr/bin/env python3
"""Audit size descriptors across all 330 monsters; no catalog modifications."""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
CANDIDATE = ROOT / "publication-candidate-text-reviewed.json"
OUT = ROOT / "size-descriptor-audit.txt"
SIZE = re.compile(r"^(Tiny|Small|Medium|Large|Huge|Gargantuan)(?: or (Tiny|Small|Medium|Large|Huge|Gargantuan))?\s+(.+)$")

def main():
    original = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))["monsters"]
    by_name = {m["name"]: m for m in candidate}
    if len(original) != 330 or len(candidate) != 330:
        raise SystemExit("Expected 330 source and candidate monsters")
    issues, multiple, unparsed = [], [], []
    for record in original:
        name = record["name"]
        lines = [line.strip() for line in record["cleaned_excerpt"].splitlines() if line.strip()]
        try:
            idx = lines.index(name)
        except ValueError:
            unparsed.append(f"{name}: monster title missing")
            continue
        if idx + 1 >= len(lines):
            unparsed.append(f"{name}: descriptor missing")
            continue
        descriptor = lines[idx + 1]
        match = SIZE.match(descriptor)
        if not match:
            unparsed.append(f"{name}: unrecognized descriptor {descriptor!r}")
            continue
        first, second, _ = match.groups()
        expected = first + (" or " + second if second else "")
        actual = by_name[name]["size"]
        if second:
            multiple.append(f"{name}: source size {expected!r}; candidate {actual!r}")
        if expected != actual:
            issues.append(f"{name}: expected {expected!r}; candidate {actual!r}")
    lines = [
        "SRD 5.2.1 SIZE DESCRIPTOR AUDIT — REVIEW ONLY",
        f"Source records: {len(original)}",
        f"Candidate monsters: {len(candidate)}",
        f"Multiple-size monsters: {len(multiple)}",
        f"Size mismatches: {len(issues)}",
        f"Unparsed descriptors: {len(unparsed)}",
        "",
        "MULTIPLE-SIZE SOURCE DESCRIPTORS:", *(multiple or ["none"]),
        "", "SIZE MISMATCHES:", *(issues or ["none"]),
        "", "UNPARSED DESCRIPTORS:", *(unparsed or ["none"]),
        "", "No published, candidate, or custom monsters modified.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:6]))
    print("Report: " + str(OUT))

if __name__ == "__main__":
    main()
