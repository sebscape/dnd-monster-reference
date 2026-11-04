#!/usr/bin/env python3
"""Preview reviewed PDF line-end hyphen joins without changing source data.

Reads the existing candidate audit; retains the legitimate 'foot-wide' compound.
Writes only a staging preview and audit report.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
REPORT = ROOT / "hyphenation-candidates-report.txt"
SOURCE = ROOT / "monster-excerpts-cleaned.json"
OUT = ROOT / "hyphenation-normalization-preview.txt"
CANDIDATE = re.compile(r"^\s+([A-Za-z]{2,})-([a-z]{2,}) \(([^)]+)\) \| (\d+) \| ", re.M)
LINE_JOIN = re.compile(r"([A-Za-z]{2,})-\s*\n\s*([a-z]{2,})")
KEEP_HYPHEN = {"foot-wide"}

def main():
    report = REPORT.read_text(encoding="utf-8")
    candidates = CANDIDATE.findall(report)
    if len(candidates) != 177:
        raise SystemExit(f"Expected 177 reviewed candidate patterns; got {len(candidates)}")
    approved = {}
    for left, right, proposed, count in candidates:
        pair = f"{left}-{right}"
        if proposed != left + right:
            raise SystemExit(f"Unexpected proposed join: {pair} -> {proposed}")
        if pair not in KEEP_HYPHEN:
            approved[(left, right)] = proposed
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = data["records"]
    if len(records) != 330:
        raise SystemExit(f"Expected 330 monsters, got {len(records)}")
    changed = Counter()
    retained = Counter()
    unknown = Counter()
    previews = []
    for record in records:
        name = record["name"]
        original = record["cleaned_excerpt"]
        def replace(match):
            left, right = match.groups()
            pair = f"{left}-{right}"
            if pair in KEEP_HYPHEN:
                retained[pair] += 1
                return left + "-" + right
            if (left, right) in approved:
                changed[pair] += 1
                return approved[(left, right)]
            unknown[pair] += 1
            return match.group(0)
        updated = LINE_JOIN.sub(replace, original)
        if name in {"Aboleth", "Cloud Giant", "Ancient Bronze Dragon", "Behir"}:
            previews.append((name, original, updated))
    lines = [
        "SRD HYPHENATION NORMALIZATION — PREVIEW ONLY",
        f"Monsters inspected: {len(records)}",
        f"Approved patterns: {len(approved)}",
        f"Joined occurrences: {sum(changed.values())}",
        f"Retained legitimate compound occurrences: {sum(retained.values())}",
        f"Unreviewed occurrences: {sum(unknown.values())}",
        "",
        "Retained: " + ", ".join(f"{k} ({v})" for k, v in retained.items()),
        "Unreviewed: " + (", ".join(f"{k} ({v})" for k, v in unknown.items()) or "none"),
        "",
        "SELECTED WORD REPLACEMENTS:",
    ]
    for pair, count in changed.most_common(30):
        lines.append(f"  {pair} -> {pair.replace('-', '')} ({count})")
    lines += ["", "PREVIEW EXCERPTS (first 650 characters after first Traits/Actions heading):"]
    for name, original, updated in previews:
        pos = updated.find("\nTraits\n")
        if pos < 0:
            pos = updated.find("\nActions\n")
        lines.append(f"=== {name} ===")
        lines.append(updated[max(pos, 0):max(pos, 0)+650].replace("\n", " "))
    lines += ["", "No source, published, or custom monster records were modified."]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Joined occurrences: {sum(changed.values())}")
    print(f"Retained legitimate compounds: {sum(retained.values())}")
    print(f"Unreviewed occurrences: {sum(unknown.values())}")
    print(f"Report: {OUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
