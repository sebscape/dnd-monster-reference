#!/usr/bin/env python3
"""Download the official SRD 5.2.1 and stage its monster text for human review.

No extracted text is automatically published as a monster stat block.
Requires: python -m pip install pymupdf
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = "https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf"
ATTRIBUTION = ('This work includes material from the System Reference Document 5.2.1 '
               '(“SRD 5.2.1”) by Wizards of the Coast LLC, available at '
               'https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under '
               'the Creative Commons Attribution 4.0 International License, '
               'available at https://creativecommons.org/licenses/by/4.0/legalcode.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, help="Use a previously downloaded official PDF")
    parser.add_argument("--out", type=Path, default=Path("staging/srd-5.2.1"))
    args = parser.parse_args()
    try:
        import fitz
    except ImportError as exc:
        raise SystemExit("Install PyMuPDF first: python -m pip install pymupdf") from exc
    args.out.mkdir(parents=True, exist_ok=True)
    pdf = args.pdf or args.out / "SRD_CC_v5.2.1.pdf"
    if not pdf.exists():
        print("Downloading official SRD 5.2.1...")
        request = Request(SOURCE, headers={"User-Agent": "MonsterReferenceImporter/0.1"})
        with urlopen(request, timeout=90) as response:
            pdf.write_bytes(response.read())
    if pdf.read_bytes()[:4] != b"%PDF":
        raise SystemExit("Source file is not a PDF")
    doc = fitz.open(pdf)
    pages = []
    for index, page in enumerate(doc):
        pages.append({"pdf_page": index + 1, "text": page.get_text("text", sort=True)})
    # Stage all pages to avoid mistakenly dropping monsters because PDF
    # heading detection or page boundaries differ across editions.
    payload = {
        "source": SOURCE,
        "license": "CC BY 4.0",
        "attribution": ATTRIBUTION,
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "page_count": len(pages),
        "status": "RAW_EXTRACTION_ONLY_NOT_VALIDATED",
        "pages": pages,
    }
    output = args.out / "extracted-pages.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Staged {len(pages)} pages in {output}")
    print("NEXT: review and map the Monsters A–Z and Animals stat blocks.")
    print("No monster catalog files were modified.")

if __name__ == "__main__":
    main()
