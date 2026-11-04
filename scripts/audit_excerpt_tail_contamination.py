#!/usr/bin/env python3
"""Find likely next-heading contamination at the end of monster excerpts.

Read-only audit. Reports all suspicious endings; does not auto-delete text.
"""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-excerpts-cleaned.json"
OUT = ROOT / "excerpt-tail-contamination-audit.txt"
HEADING = re.compile(r"(?:^|[.!?]\s+)([A-Z][A-Za-z’'’-]*(?:\s+[A-Z][A-Za-z’'’-]*){0,3})\s*$")
def main():
    records = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    flagged = []
    endings = []
    for i, record in enumerate(records):
        name = record["name"]
        next_name = records[i+1]["name"] if i+1 < len(records) else None
        lines = [line.strip() for line in record["cleaned_excerpt"].splitlines() if line.strip()]
        tail = lines[-1] if lines else ""
        match = HEADING.search(tail)
        candidate = match.group(1) if match else None
        reason = None
        if candidate:
            reason = "possible terminal heading"
        if next_name and tail.endswith(next_name):
            reason = "ends with next monster name"
        if reason:
            flagged.append((name, next_name, candidate, tail, reason))
        endings.append((name, tail))
    lines = [
        "SRD EXCERPT TAIL CONTAMINATION AUDIT — REVIEW ONLY",
        f"Records inspected: {len(records)}",
        f"Potentially contaminated endings: {len(flagged)}",
        "",
        "FLAGGED ENDINGS (do not remove automatically):",
    ]
    for name, next_name, candidate, tail, reason in flagged:
        lines.extend([
            f"=== {name} ===",
            f"  Next indexed monster: {next_name}",
            f"  Reason: {reason}; terminal candidate: {candidate!r}",
            f"  Last source line: {tail[-400:]}",
        ])
    lines.extend(["", "ALL EXCERPT ENDINGS (last 160 characters):"])
    for name, tail in endings:
        lines.append(f"  {name}: {tail[-160:]}")
    lines.extend(["", "No staging, published, or custom monster records were modified."])
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Records inspected: {len(records)}")
    print(f"Potentially contaminated endings: {len(flagged)}")
    print(f"Report: {OUT}")
    print("No staging, published, or custom monster records were modified.")

if __name__ == "__main__":
    main()
