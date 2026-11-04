#!/usr/bin/env python3
"""Audit PDF line-end hyphenation in staged monster features.

Read-only diagnostic: propose joins but never rewrite source excerpts.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
data = json.loads((ROOT / "monster-excerpts-cleaned.json").read_text(encoding="utf-8"))
records = data["records"]
if len(records) != 330:
    raise SystemExit(f"Expected 330 records; found {len(records)}")
# Only hyphens at a physical PDF line ending are considered.
pattern = re.compile(r"([A-Za-z]{2,})-\s*\n\s*([a-z]{2,})")
counts = Counter()
examples = {}
for record in records:
    raw = record["cleaned_excerpt"]
    for match in pattern.finditer(raw):
        left, right = match.groups()
        pair = f"{left}-{right}"
        counts[pair] += 1
        if pair not in examples:
            examples[pair] = record["name"]
report = [
    "SRD line-end hyphenation candidates — REVIEW ONLY",
    f"Excerpts: {len(records)}",
    f"Candidate occurrences: {sum(counts.values())}",
    f"Distinct candidates: {len(counts)}",
    "",
    "All candidate joins (hyphen retained in left-right; proposed joined word in parentheses):",
]
for pair, count in counts.most_common():
    report.append(f"  {pair} ({pair.replace('-', '')}) | {count} | {examples[pair]}")
report += [
    "",
    "CAUTION: Some source words are legitimately hyphenated.",
    "No automatic replacements have been made.",
    "No published or custom monsters were modified.",
]
output = ROOT / "hyphenation-candidates-report.txt"
output.write_text("\n".join(report) + "\n", encoding="utf-8")
print(f"Candidate occurrences: {sum(counts.values())}")
print(f"Distinct candidates: {len(counts)}")
print(f"Report: {output}")
print("No published or custom monsters were modified.")

