#!/usr/bin/env python3
"""Slice SRD monster text using audited boundaries; staging only.

The resulting excerpts are NOT validated stat blocks and must not be
imported into the published catalog.
"""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "monster-columns-all.txt"
AUDIT = ROOT / "monster-boundary-audit.json"
OUT = ROOT / "monster-excerpts.json"
REPORT = ROOT / "monster-excerpts-report.txt"

def main():
    if not SOURCE.exists() or not AUDIT.exists():
        raise SystemExit("Run column extraction and boundary audit first.")
    raw = SOURCE.read_text(encoding="utf-8")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    boundaries = audit["boundaries"]
    if len(boundaries) != 330 or audit["missing_names"] != ["Animals"] or audit["duplicate_names"] or audit["indexed_page_mismatches"]:
        raise SystemExit("Boundary audit differs from expected results; inspect before slicing.")
    if any(b["offset"] >= n["offset"] for b, n in zip(boundaries, boundaries[1:])):
        raise SystemExit("Offsets are not strictly increasing.")
    records = []
    anomalies = []
    for i, b in enumerate(boundaries):
        start = b["offset"]
        end = boundaries[i + 1]["offset"] if i + 1 < len(boundaries) else len(raw)
        excerpt = raw[start:end]
        # Keep page/column markers for review, but flag missing stat signals.
        checks = {
            "name_at_start": excerpt.lstrip().startswith(b["name"]),
            "has_ac": bool(re.search(r"(?m)^AC\s+\d+", excerpt)),
            "has_hp": bool(re.search(r"(?m)^HP\s+\d+", excerpt)),
            "has_cr": bool(re.search(r"(?m)^CR\s+(?:\d+/\d+|\d+)", excerpt)),
        }
        if not all(checks.values()):
            anomalies.append({"name": b["name"], "checks": checks})
        records.append({
            "name": b["name"],
            "start_pdf_page": b["pdf_page"],
            "start_column": b["column"],
            "review_status": "UNVERIFIED_EXCERPT",
            "checks": checks,
            "raw_excerpt": excerpt.strip(),
        })
    OUT.write_text(json.dumps({
        "status": "UNVERIFIED_NOT_FOR_IMPORT",
        "count": len(records),
        "records": records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    report = [
        f"Excerpts: {len(records)}",
        f"Records missing a basic signal: {len(anomalies)}",
        "No excerpt is approved for import.",
        "",
        "ANOMALIES:",
        *[f"  {a['name']}: {a['checks']}" for a in anomalies],
        "",
        "PILOT SIZES:",
        *[f"  {r['name']}: {len(r['raw_excerpt'])} chars" for r in records
          if r["name"] in {"Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat"}],
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:3]))
    print(f"Report: {REPORT}")
    print(f"Excerpts: {OUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
