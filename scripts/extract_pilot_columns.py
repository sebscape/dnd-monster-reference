#!/usr/bin/env python3
"""Extract pilot monster PDF pages by column using PyMuPDF geometry.

Creates local review artifacts only. Does not modify published/custom records.
"""
import json
from pathlib import Path
import pymupdf

ROOT = Path("staging/srd-5.2.1")
INVENTORY = ROOT / "stat-block-inventory.json"
PDF = ROOT / "SRD_CC_v5.2.1.pdf"
PILOTS = ("Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat")

def find_pdf():
    if PDF.exists():
        return PDF
    candidates = list(ROOT.glob("*.pdf"))
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit(
        "PDF not found in staging/srd-5.2.1. "
        "Place SRD_CC_v5.2.1.pdf there, or rerun scripts/stage_srd.py "
        "if that script retains the PDF."
    )

def column_text(page, left, right):
    blocks = page.get_text("blocks", sort=True)
    selected = []
    for b in blocks:
        if len(b) < 5 or not isinstance(b[4], str):
            continue
        x0, y0, x1, y1 = b[:4]
        center = (x0 + x1) / 2
        if left <= center < right and y0 < page.rect.height - 22:
            selected.append((y0, x0, b[4].strip()))
    selected.sort()
    return "\n\n".join(t for _, _, t in selected if t)

def main():
    if not INVENTORY.exists():
        raise SystemExit("Run scripts/build_stat_block_inventory.py first.")
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    lookup = {e["name"]: e["indexed_pdf_page"] for e in inv["entries"]}
    path = find_pdf()
    doc = pymupdf.open(path)
    out = ROOT / "pilot-columns.txt"
    lines = [
        "PILOT COLUMN EXTRACTION — UNVERIFIED",
        "Each page is divided at its geometric midpoint; inspect for spillover.",
        "Page numbers are 1-based. Some entries continue on later pages.",
        "",
    ]
    for name in PILOTS:
        page_num = lookup.get(name)
        if page_num is None:
            lines.extend([f"NOT INDEXED: {name}", ""])
            continue
        page = doc[page_num - 1]
        mid = (page.rect.x0 + page.rect.x1) / 2
        lines.extend([
            f"================ {name} / PDF page {page_num} ================",
            "---------- LEFT COLUMN ----------",
            column_text(page, page.rect.x0, mid),
            "---------- RIGHT COLUMN ----------",
            column_text(page, mid, page.rect.x1 + 1),
            "",
        ])
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Created {out}")
    print("Pilot pages:", ", ".join(f"{name}={lookup.get(name, 'missing')}" for name in PILOTS))
    print("No published or custom monster records were modified.")

if __name__ == "__main__":
    main()
