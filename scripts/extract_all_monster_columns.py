#!/usr/bin/env python3
"""Create a geometry-preserving review text for all SRD monster pages.

Reading order is left column then right column, page by page.
This is staged source text, NOT parsed or validated monster data.
"""
import json
from pathlib import Path
import pymupdf

ROOT = Path("staging/srd-5.2.1")
INDEX = ROOT / "stat-block-inventory.json"
OUT = ROOT / "monster-columns-all.txt"
FIRST, LAST = 258, 364

def main():
    if not INDEX.exists():
        raise SystemExit("Run scripts/build_stat_block_inventory.py first.")
    inv = json.loads(INDEX.read_text(encoding="utf-8"))
    candidates = list(ROOT.glob("*.pdf"))
    preferred = ROOT / "SRD_CC_v5.2.1.pdf"
    if preferred.exists():
        pdf = preferred
    elif len(candidates) == 1:
        pdf = candidates[0]
    else:
        raise SystemExit("Expected one SRD PDF in staging/srd-5.2.1.")
    by_page = {}
    for entry in inv["entries"]:
        by_page.setdefault(entry["indexed_pdf_page"], []).append(entry["name"])
    doc = pymupdf.open(pdf)
    lines = [
        "SRD 5.2.1 — MONSTER PAGES IN READING ORDER",
        "STAGING ONLY: text is not yet assigned to individual monsters.",
        "Columns are split at page midpoint using text block centers.",
        "Long blocks spanning the midpoint may need manual review.",
        "",
    ]
    for n in range(FIRST, LAST + 1):
        page = doc[n - 1]
        midpoint = (page.rect.x0 + page.rect.x1) / 2
        blocks = page.get_text("blocks")
        cols = [[], []]
        for b in blocks:
            if len(b) < 5 or not isinstance(b[4], str):
                continue
            x0, y0, x1, y1 = b[:4]
            if y0 >= page.rect.height - 22:
                continue
            col = 0 if (x0 + x1) / 2 < midpoint else 1
            cols[col].append((y0, x0, b[4].strip()))
        lines.append(f"========== PDF PAGE {n} | INDEX: {', '.join(by_page.get(n, []))} ==========")
        for col, title in zip(cols, ("LEFT", "RIGHT")):
            lines.append(f"---------- {title} ----------")
            lines.extend(text for _, _, text in sorted(col) if text)
        lines.append("")
    OUT.write_text("\n\n".join(lines), encoding="utf-8")
    print(f"Created {OUT} ({OUT.stat().st_size:,} bytes)")
    print(f"Pages processed: {LAST - FIRST + 1}")
    print("No published or custom monster records were modified.")

if __name__ == "__main__":
    main()
