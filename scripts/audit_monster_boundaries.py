#!/usr/bin/env python3
"""Audit stat-block starts in column-ordered SRD text. Never imports monsters."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
INDEX = ROOT / "stat-block-inventory.json"
COLUMNS = ROOT / "monster-columns-all.txt"
OUTPUT = ROOT / "monster-boundary-audit.json"
REPORT = ROOT / "monster-boundary-audit.txt"
SIZE = r"(?:Tiny|Small|Medium|Large|Huge|Gargantuan)"

def main():
    if not INDEX.exists() or not COLUMNS.exists():
        raise SystemExit("Missing inventory or monster-columns-all.txt in staging/srd-5.2.1")
    inventory = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = {item["name"]: item for item in inventory["entries"]}
    lines = COLUMNS.read_text(encoding="utf-8").splitlines(keepends=True)
    candidates = []
    offset = 0
    page = None
    column = None
    for i, line in enumerate(lines):
        match = re.match(r"=+ PDF PAGE (\d+) \|", line)
        if match:
            page = int(match.group(1))
        if "---------- LEFT" in line:
            column = "left"
        elif "---------- RIGHT" in line:
            column = "right"
        name = line.strip()
        if name in entries:
            following = "".join(lines[i + 1:i + 12])
            pattern = rf"^\s*(?:{re.escape(name)}\s*)?{SIZE}\b[^\n]{{0,130}}\n\s*AC\s+\d+"
            if re.search(pattern, following):
                candidates.append({"name": name, "pdf_page": page, "column": column, "offset": offset})
        offset += len(line)
    # Section headings sometimes repeat the monster name immediately before
    # the actual title. Collapse only adjacent same-name candidates.
    boundaries = []
    for item in candidates:
        if (boundaries and boundaries[-1]["name"] == item["name"]
                and item["offset"] - boundaries[-1]["offset"] < 150):
            boundaries[-1] = item
        else:
            boundaries.append(item)
    counts = Counter(item["name"] for item in boundaries)
    missing = sorted(set(entries) - set(counts))
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    page_mismatches = [
        item for item in boundaries
        if item["pdf_page"] != entries[item["name"]]["indexed_pdf_page"]
    ]
    result = {
        "status": "BOUNDARY_AUDIT_ONLY_NOT_VALIDATED",
        "indexed_count": len(entries),
        "boundary_count": len(boundaries),
        "unique_names": len(counts),
        "missing_names": missing,
        "duplicate_names": duplicates,
        "indexed_page_mismatches": page_mismatches,
        "boundaries": boundaries,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report = [
        f"Indexed entries: {len(entries)}",
        f"Boundary candidates: {len(boundaries)}",
        f"Unique matched names: {len(counts)}",
        f"Missing: {len(missing)}",
        f"Duplicates: {len(duplicates)}",
        f"Indexed-page mismatches: {len(page_mismatches)}",
        "",
        "MISSING:", *[f"  {name}" for name in missing],
        "DUPLICATES:", *[f"  {name}" for name in duplicates],
        "PAGE MISMATCHES:",
        *[f"  {x['name']}: index {entries[x['name']]['indexed_pdf_page']}, found {x['pdf_page']}" for x in page_mismatches],
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:6]))
    print(f"Report: {REPORT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
