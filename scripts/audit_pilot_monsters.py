#!/usr/bin/env python3
"""Create a read-only pilot audit for selected SRD stat blocks.

This does NOT convert entries: the extracted PDF has interleaved columns,
so numeric values on a page must not be assigned to names without review.
"""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "extracted-pages.json"
INDEX = ROOT / "stat-block-inventory.json"
OUT = ROOT / "pilot-stat-block-audit.txt"
PILOTS = ("Aboleth", "Goblin Minion", "Skeleton", "Zombie", "Giant Rat")
FIELD = re.compile(r"\b(?:AC\s+\d+|HP\s+\d+|Initiative\s*[+−-]?\d+|Speed\s+\d+|CR\s+(?:\d+/\d+|\d+))\b", re.I)

def main():
    if not SOURCE.exists() or not INDEX.exists():
        raise SystemExit("Run stage_srd.py and build_stat_block_inventory.py first.")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    pages = {p["pdf_page"]: p["text"] for p in data["pages"]}
    entries = {e["name"]: e for e in index["entries"]}
    lines = [
        "SRD 5.2.1 pilot audit — NOT VALIDATED",
        "WARNING: Multiple monsters share PDF pages; values below are PAGE-LEVEL evidence only.",
        "Never assign these values to a named monster automatically.",
        "",
    ]
    for name in PILOTS:
        entry = entries.get(name)
        if not entry:
            lines.extend([f"{name}: NOT FOUND IN INVENTORY", ""])
            continue
        page = entry["indexed_pdf_page"]
        text = pages[page]
        matches = [m.group(0) for m in FIELD.finditer(text)]
        lines.extend([
            f"=== {name} — PDF page {page} ===",
            "Page-level stat signals (may belong to other monsters):",
            "  " + (" | ".join(matches[:50]) if matches else "none"),
            "Text around first exact name occurrence:",
        ])
        match = re.search(re.escape(name), text, re.I)
        if match:
            lines.append("  " + text[max(0, match.start()-150):match.end()+1100].replace("\n", " | "))
        else:
            lines.append("  Name not found verbatim")
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Pilot audit created: {OUT}")
    print("Pilot names: " + ", ".join(PILOTS))
    print("No monster records were created or changed.")

if __name__ == "__main__":
    main()
