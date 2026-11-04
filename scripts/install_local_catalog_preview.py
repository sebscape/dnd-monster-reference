#!/usr/bin/env python3
"""Install a local-only preview catalog for Vite. Never changes live catalog."""
import json
from pathlib import Path

SRC = Path("staging/srd-5.2.1/publication-candidate-review.json")
DEST = Path("public/data/published-monsters-preview.json")
LIVE = Path("public/data/published-monsters.json")
REPORT = Path("staging/srd-5.2.1/local-preview-report.txt")

def main():
    candidate = json.loads(SRC.read_text(encoding="utf-8"))
    published = json.loads(LIVE.read_text(encoding="utf-8"))
    monsters = candidate["monsters"]
    old = {m["name"]: m["id"] for m in published["monsters"]}
    ids = [m["id"] for m in monsters]
    if len(monsters) != 330 or len(set(ids)) != 330:
        raise SystemExit("Expected 330 unique monsters; preview not installed")
    by_name = {m["name"]: m["id"] for m in monsters}
    if len(old) != 4 or any(by_name.get(name) != mid for name, mid in old.items()):
        raise SystemExit("Seed ID preservation check failed; preview not installed")
    if candidate.get("schema_version") != "1.2.0":
        raise SystemExit("Unexpected schema; preview not installed")
    candidate["source"] = dict(candidate.get("source", {}))
    candidate["source"]["modifications"] = (
        "Original SRD 5.2.1 stat-block text extracted and reorganized into structured JSON; "
        "line wraps and PDF hyphenation normalized; non-stat-block group headings removed. "
        "Young White Dragon Intelligence saving throw printed unsigned 2 on PDF p. 340 "
        "and provisionally interpreted as +2."
    )
    DEST.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "LOCAL SRD PREVIEW — NOT PUBLISHED",
        f"Preview monsters: {len(monsters)}",
        "Preserved original published IDs: 4",
        f"Preview file: {DEST}",
        "Live published catalog unchanged: " + str(LIVE),
        "Start Vite with: npm run dev",
        "Open preview: http://localhost:5173/?catalog=preview",
        "Open original: http://localhost:5173/",
        "If Vite uses a different port, keep its shown URL and append ?catalog=preview.",
        "Custom monsters use existing browser localStorage in both views; export a backup first.",
        "This is a UI test, not confirmation of PDF transcription accuracy.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
