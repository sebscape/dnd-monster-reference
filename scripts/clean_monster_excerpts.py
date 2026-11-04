#!/usr/bin/env python3
"""Produce cleaned, review-only SRD excerpts without changing originals."""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
source = ROOT / "monster-excerpts.json"
output = ROOT / "monster-excerpts-cleaned.json"
report = ROOT / "monster-cleaning-report.txt"

page_header = re.compile(r"^=+ PDF PAGE [0-9]+ \| INDEX: .* =+$")
column_marker = re.compile(r"^-+ (LEFT|RIGHT) -+$")
footer = "System Reference Document 5.2.1"

AUDITED_TAIL_HEADINGS = {
    "Air Elemental": "Animated Objects",
    "Assassin": "Awakened Plants",
    "Axe Beak": "Azer",
    "Balor": "Bandits",
    "Berserker": "Black Dragons",
    "Blink Dog": "Blue Dragons",
    "Bone Devil": "Brass Dragons",
    "Ancient Brass Dragon": "Bronze Dragons",
    "Ancient Bronze Dragon": "Bugbears",
    "Bulette": "Centaur",
    "Commoner": "Copper Dragons",
    "Couatl": "Crawling Claw",
    "Swarm of Crawling Claws": "Cultists",
    "Frost Giant": "Fungi",
    "Gladiator": "Gnoll",
    "Gnoll Warrior": "Goblins",
    "Goblin Boss": "Gold Dragons",
    "Gray Ooze": "Green Dragons",
    "Guardian Naga": "Guards",
    "Hippogriff": "Hobgoblins",
    "Knight": "Kobold",
    "Lich": "Mages",
    "Medusa": "Mephits",
    "Steam Mephit": "Merfolk",
    "Minotaur of Baphomet": "Mummies",
    "Phase Spider": "Pirates",
    "Planetar": "Priests",
    "Rakshasa": "Red Dragons",
    "Rust Monster": "Sahuagin",
    "Shield Guardian": "Silver Dragons",
    "Ancient Silver Dragon": "Skeletons",
    "Specter": "Sphinxes",
    "Tarrasque": "Toughs",
    "Unicorn": "Vampires",
    "Vrock": "Warriors",
    "Werewolf": "White Dragons",
    "Xorn": "Zombies",
    "Ogre Zombie": "Animals",
}


def clean(raw, following_name, current_name):
    kept = []
    removed = []
    for line in raw.splitlines():
        stripped = line.strip()
        reason = None
        if page_header.fullmatch(stripped):
            reason = "page header"
        elif column_marker.fullmatch(stripped):
            reason = "column marker"
        elif stripped == footer:
            reason = "document footer"
        elif re.fullmatch(r"[0-9]{3}", stripped) and 258 <= int(stripped) <= 364:
            reason = "page number"
        if reason:
            removed.append({"reason": reason, "text": stripped})
        else:
            kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    if following_name and kept and kept[-1].strip() == following_name:
        removed.append({"reason": "next monster heading", "text": kept.pop().strip()})
    # Group headings at the end of the preceding excerpt are PDF navigation text.
    # Remove only the explicitly audited 38 headings, keyed by current monster.
    if current_name in AUDITED_TAIL_HEADINGS and kept and kept[-1].strip() == AUDITED_TAIL_HEADINGS[current_name]:
        removed.append({"reason": "audited next group heading", "text": kept.pop().strip()})
    return "\n".join(kept).strip(), removed

def main():
    data = json.loads(source.read_text(encoding="utf-8"))
    records = data["records"]
    if len(records) != 330:
        raise SystemExit("Unexpected excerpt count; refusing cleanup.")
    cleaned_records = []
    counts = {}
    failed = []
    for index, record in enumerate(records):
        following = records[index + 1]["name"] if index + 1 < len(records) else None
        cleaned, removed = clean(record["raw_excerpt"], following, record["name"])
        for item in removed:
            reason = item["reason"]
            counts[reason] = counts.get(reason, 0) + 1
        checks = {
            "name_at_start": cleaned.startswith(record["name"] + "\n"),
            "has_ac": bool(re.search(r"(?m)^AC\s+\d+", cleaned)),
            "has_hp": bool(re.search(r"(?m)^HP\s+\d+", cleaned)),
            "has_cr": bool(re.search(r"(?m)^CR\s+(?:\d+/\d+|\d+)", cleaned)),
        }
        if not all(checks.values()):
            failed.append(record["name"])
        cleaned_records.append({
            "name": record["name"],
            "start_pdf_page": record["start_pdf_page"],
            "review_status": "UNVERIFIED_CLEANED_TEXT_NOT_FOR_IMPORT",
            "checks": checks,
            "removed_lines": removed,
            "cleaned_excerpt": cleaned,
        })
    output.write_text(json.dumps({
        "status": "NOT_FOR_IMPORT", "count": len(cleaned_records),
        "records": cleaned_records
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"Cleaned excerpts: {len(cleaned_records)}",
        f"Missing basic signals after cleanup: {len(failed)}",
        "Removed lines by category:",
        *[f"  {name}: {count}" for name, count in sorted(counts.items())],
        "Possible section headings intentionally retained for review.",
        "Original excerpts and published/custom monsters unchanged.",
        "", "FAILED CHECKS:", *[f"  {name}" for name in failed],
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:len(counts) + 5]))
    print(f"Report: {report}")
    print(f"Cleaned copy: {output}")

if __name__ == "__main__":
    main()
