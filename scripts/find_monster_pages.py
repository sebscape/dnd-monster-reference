#!/usr/bin/env python3
"""Find likely monster stat-block pages in staged SRD 5.2.1 text.

Produces a review report only; never changes the published catalog.
"""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SOURCE = ROOT / "extracted-pages.json"
OUTPUT = ROOT / "monster-candidates.json"
REPORT = ROOT / "monster-candidates.txt"

# Use several distinctive stat-block signals together rather than assuming
# a fixed page range or treating every occurrence of 'Challenge' as a monster.
ABILITY_ROW = re.compile(r"\\bSTR\\b.{0,90}\\bDEX\\b.{0,90}\\bCON\\b", re.I | re.S)
AC = re.compile(r"\\bArmor Class\\b", re.I)
HP = re.compile(r"\\bHit Points\\b", re.I)
CR = re.compile(r"\\b(?:Challenge|CR)\\s*(?:Rating)?\\b", re.I)
INIT = re.compile(r"\\bInitiative\\b", re.I)
SPEED = re.compile(r"\\bSpeed\\b", re.I)

def main():
    if not SOURCE.exists():
        raise SystemExit("Missing staged extraction. Run: python scripts/stage_srd.py")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidates = []
    for page in data["pages"]:
        content = page["text"]
        signals = {
            "armor_class": bool(AC.search(content)),
            "hit_points": bool(HP.search(content)),
            "challenge": bool(CR.search(content)),
            "ability_headers": bool(ABILITY_ROW.search(content)),
            "initiative": bool(INIT.search(content)),
            "speed": bool(SPEED.search(content)),
        }
        score = sum(signals.values())
        if score < 4 or not (signals["armor_class"] and signals["hit_points"]):
            continue
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        # Human-readable page excerpts, not machine-verified monster records.
        markers = [i for i, line in enumerate(lines) if AC.search(line)]
        excerpts = []
        for i in markers[:12]:
            excerpts.append(" | ".join(lines[max(0, i - 5):min(len(lines), i + 9)])[:700])
        candidates.append({
            "pdf_page": page["pdf_page"],
            "score": score,
            "signals": signals,
            "armor_class_mentions": len(markers),
            "excerpts": excerpts,
            "review_status": "unreviewed",
        })
    result = {
        "source_pdf_sha256": data.get("pdf_sha256"),
        "status": "CANDIDATE_PAGES_ONLY_NOT_MONSTER_RECORDS",
        "candidate_page_count": len(candidates),
        "candidates": candidates,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT.write_text("\\n".join(
        f"PDF page {c['pdf_page']} | score {c['score']}/6 | AC mentions {c['armor_class_mentions']}\\n" +
        "\\n".join("  " + e for e in c["excerpts"]) for c in candidates
    ).replace("\\n", "\n"), encoding="utf-8")
    print(f"Found {len(candidates)} candidate pages (not verified monster counts).")
    print(f"Review report: {REPORT}")
    print(f"Structured candidates: {OUTPUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
