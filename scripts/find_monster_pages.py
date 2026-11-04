#!/usr/bin/env python3
"""Diagnose and locate potential SRD 5.2.1 monster pages without modifying the catalog."""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "extracted-pages.json"
OUTPUT = ROOT / "monster-candidates.json"
REPORT = ROOT / "monster-candidates.txt"

# Flexible matching: the PDF may split labels, reorder columns, or omit
# familiar 2014-style stat-block labels in the 2024/2025 SRD.
SIGNALS = {
    "armor_class": re.compile(r"armor\s*class|\bAC\s*\d", re.I),
    "hit_points": re.compile(r"hit\s*points|\bHP\s*\d", re.I),
    "challenge": re.compile(r"challenge(?:\s*rating)?|\bCR\s*\d", re.I),
    "ability_scores": re.compile(r"\bSTR\b|\bDEX\b|\bCON\b", re.I),
    "initiative": re.compile(r"\binitiative\b", re.I),
    "speed": re.compile(r"\bspeed\b", re.I),
    "actions": re.compile(r"\bactions\b|\bbonus\s*actions\b", re.I),
}

def main():
    if not SOURCE.exists():
        raise SystemExit("Missing extraction. Run python scripts/stage_srd.py")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    pages = data.get("pages", [])
    totals = {name: 0 for name in SIGNALS}
    candidates = []
    nonempty = 0
    for page in pages:
        raw = page.get("text", "")
        if raw.strip():
            nonempty += 1
        # Normalize all whitespace for broken line wrapping.
        normalized = re.sub(r"\s+", " ", raw)
        found = {name: bool(pattern.search(normalized)) for name, pattern in SIGNALS.items()}
        for name, hit in found.items():
            totals[name] += int(hit)
        score = sum(found.values())
        if score < 2:
            continue
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        excerpts = []
        for i, line in enumerate(lines):
            if any(pattern.search(line) for pattern in (SIGNALS["armor_class"], SIGNALS["hit_points"], SIGNALS["challenge"])):
                excerpts.append(" | ".join(lines[max(0, i - 2):i + 6])[:450])
                if len(excerpts) >= 8:
                    break
        candidates.append({
            "pdf_page": page.get("pdf_page"),
            "score": score,
            "signals": found,
            "excerpts": excerpts,
            "review_status": "unreviewed",
        })
    result = {
        "source_pdf_sha256": data.get("pdf_sha256"),
        "status": "DIAGNOSTIC_CANDIDATE_PAGES_NOT_VERIFIED_MONSTERS",
        "total_pages": len(pages),
        "pages_with_text": nonempty,
        "pages_containing_signals": totals,
        "candidate_page_count": len(candidates),
        "candidates": candidates,
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        f"Pages: {len(pages)}; pages with text: {nonempty}",
        "Pages containing each signal:",
        *[f"  {key}: {value}" for key, value in totals.items()],
        f"Candidate pages with 2+ signals: {len(candidates)}",
        "",
    ]
    for candidate in candidates:
        lines.append(f"PDF page {candidate['pdf_page']} | score {candidate['score']}/7")
        lines.extend("  " + e for e in candidate["excerpts"])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:len(totals) + 4]))
    print(f"Review report: {REPORT}")
    print(f"Structured candidates: {OUTPUT}")
    print("These are diagnostic pages, NOT validated monster records.")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
