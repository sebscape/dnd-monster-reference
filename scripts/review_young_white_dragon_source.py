#!/usr/bin/env python3
"""Inspect the Young White Dragon ability row in the official SRD PDF.

Read-only diagnostic. Produces a text report and a PNG of the source page.
Does not infer or change any saving throw.
"""
import json
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
PDF = ROOT / "SRD_CC_v5.2.1.pdf"
SOURCE = ROOT / "monster-excerpts-cleaned.json"
REPORT = ROOT / "young-white-dragon-source-review.txt"
IMAGE = ROOT / "young-white-dragon-source-page.png"

def main():
    try:
        import pymupdf
    except ImportError as exc:
        raise SystemExit("Install PyMuPDF: python -m pip install pymupdf") from exc
    if not PDF.exists():
        raise SystemExit(f"Missing original SRD PDF: {PDF}. Run scripts/stage_srd.py first.")
    records = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    matches = [r for r in records if r["name"] == "Young White Dragon"]
    if len(matches) != 1:
        raise SystemExit(f"Expected one Young White Dragon record; found {len(matches)}")
    record = matches[0]
    page_number = record["start_pdf_page"]
    doc = pymupdf.open(PDF)
    if not 1 <= page_number <= len(doc):
        raise SystemExit(f"Invalid PDF page number: {page_number}")
    page = doc[page_number - 1]
    page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).save(IMAGE)
    lines = record["cleaned_excerpt"].splitlines()
    focus = []
    for index, line in enumerate(lines):
        if line.strip().startswith(("Str ", "Dex ", "Con ", "Int ", "Wis ", "Cha ")):
            focus.append((index, line))
    around = []
    seen = set()
    for index, _ in focus:
        for j in range(max(0, index-2), min(len(lines), index+4)):
            if j not in seen:
                seen.add(j)
                around.append((j+1, lines[j]))
    report = [
        "YOUNG WHITE DRAGON — ORIGINAL SRD PDF REVIEW",
        f"Source PDF page (1-based): {page_number}",
        f"Source PDF file: {PDF}",
        f"Rendered source page: {IMAGE}",
        "",
        "ABILITY TABLE SOURCE EXCERPT (line numbers within cleaned monster excerpt):",
        *(f"  {number:3}: {value}" for number, value in sorted(around)),
        "",
        "IMPORTANT: Inspect the rendered page image visually for the Int save sign.",
        "Do not infer a missing sign from a calculated modifier.",
        "No staged, published, or custom monster records were modified.",
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Source PDF page: {page_number}")
    print(f"Report: {REPORT}")
    print(f"Rendered page: {IMAGE}")
    print("No monster records were modified.")

if __name__ == "__main__":
    main()
