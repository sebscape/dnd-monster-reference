#!/usr/bin/env python3
"""Inventory feature section headings across staged SRD monster excerpts.

Diagnostic only. Does not attempt to parse individual abilities or import data.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

root = Path("staging/srd-5.2.1")
source = root / "monster-excerpts-cleaned.json"
output = root / "feature-section-heading-audit.txt"
records = json.loads(source.read_text(encoding="utf-8"))["records"]
if len(records) != 330:
    raise SystemExit(f"Expected 330 records, got {len(records)}")

known = {
    "Traits", "Actions", "Bonus Actions", "Reactions",
    "Legendary Actions", "Mythic Actions", "Lair Actions",
}
counts = Counter()
examples = defaultdict(list)
unknown = Counter()
unknown_examples = defaultdict(list)
for record in records:
    lines = [line.strip() for line in record["cleaned_excerpt"].splitlines()]
    cr_at = next((i for i, line in enumerate(lines) if re.match(r"^CR\s+", line)), None)
    if cr_at is None:
        continue
    for i in range(cr_at + 1, len(lines)):
        line = lines[i]
        if line in known:
            counts[line] += 1
            if len(examples[line]) < 8:
                examples[line].append(record["name"])
        elif (line and len(line) <= 38 and
              re.fullmatch(r"[A-Z][A-Za-z’' -]+", line) and
              not line.endswith(".") and
              i + 1 < len(lines) and not lines[i + 1].strip()):
            unknown[line] += 1
            if len(unknown_examples[line]) < 4:
                unknown_examples[line].append(record["name"])

report = [
    "SRD feature section heading inventory — REVIEW ONLY",
    f"Excerpts examined: {len(records)}",
    "",
    "KNOWN HEADINGS (occurrences, not distinct monsters):",
]
for heading in sorted(known):
    report.append(f"  {heading}: {counts[heading]}")
    report.append("    Examples: " + ", ".join(examples[heading]))
report.extend(["", "POSSIBLE OTHER HEADINGS (heuristic; includes false positives):"])
for heading, count in unknown.most_common():
    report.append(f"  {heading}: {count} | {', '.join(unknown_examples[heading])}")
report.extend([
    "", "No ability text was parsed.",
    "No original, published, or custom monster records were modified.",
])
output.write_text("\n".join(report) + "\n", encoding="utf-8")
print(f"Excerpts examined: {len(records)}")
print(f"Possible other headings: {len(unknown)}")
print(f"Report: {output}")
print("No published or custom monsters were modified.")
