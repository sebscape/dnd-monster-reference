#!/usr/bin/env python3
"""Build an SRD 5.2.1 stat-block inventory from its printed index.

This is a review-stage inventory, NOT a monster import. The PDF has two
interleaved columns and entries may span pages. No catalog is modified.
"""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "extracted-pages.json"
DEST = ROOT / "stat-block-inventory.json"
REPORT = ROOT / "stat-block-inventory.txt"
# Index of Stat Blocks starts on PDF page 2 and continues through page 4.
ENTRY = re.compile(r"(?P<name>[A-Z][A-Za-z0-9’'(),+\- ]{1,65}?)\.{3,}\s*(?P<page>\d{3})")
STAT = re.compile(r"\bAC\s+\d+\b.{0,140}?\bInitiative\s*[+−-]?\d+", re.I | re.S)

def main():
    if not SOURCE.exists():
        raise SystemExit("Missing staged extraction: run python scripts/stage_srd.py")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    pages = {int(p["pdf_page"]): p["text"] for p in source["pages"]}
    indexed = {}
    for page_no in (2, 3, 4):
        # The index is printed in multiple columns; extract all name/dotted/page pairs.
        for match in ENTRY.finditer(pages[page_no]):
            name = " ".join(match.group("name").split())
            target = int(match.group("page"))
            if 258 <= target <= 364 and name not in indexed:
                indexed[name] = target
    entries = []
    for name, page in sorted(indexed.items(), key=lambda x: (x[1], x[0].casefold())):
        text = pages.get(page, "")
        # These are weak checks; names can be split or interleaved by the PDF.
        name_seen = bool(re.search(re.escape(name), text, re.I))
        stat_signal = bool(STAT.search(text))
        entries.append({
            "name": name,
            "indexed_pdf_page": page,
            "section": "Animals" if page >= 344 else "Monsters A-Z",
            "name_found_on_indexed_page": name_seen,
            "stat_block_signal_on_page": stat_signal,
            "review_status": "unverified",
        })
    result = {
        "source_pdf_sha256": source.get("pdf_sha256"),
        "status": "INDEX_INVENTORY_ONLY_NOT_VALIDATED",
        "count": len(entries),
        "entries": entries,
    }
    DEST.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    missing = [e for e in entries if not e["name_found_on_indexed_page"]]
    lines = [
        f"Index entries: {len(entries)}",
        f"Name found on indexed page: {len(entries) - len(missing)}",
        f"Name not found verbatim on indexed page: {len(missing)}",
        "Missing names may reflect PDF column extraction, not missing monsters.",
        "",
        "REVIEW NEEDED:",
        *[f"  p.{e['indexed_pdf_page']} {e['name']}" for e in missing],
        "",
        "ALL INDEX ENTRIES:",
        *[f"  p.{e['indexed_pdf_page']} {e['name']}" for e in entries],
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4]))
    print(f"Report: {REPORT}")
    print(f"JSON: {DEST}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
