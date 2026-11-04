#!/usr/bin/env python3
"""Publish the explicitly approved 330-monster SRD catalog to the tracked JSON file.

Run locally from repository root, then review git diff and commit/push.
Never touches browser localStorage or custom-monsters.json.
"""
import json
import shutil
from pathlib import Path

SOURCE = Path("staging/srd-5.2.1/publication-candidate-final-review.json")
DEST = Path("public/data/published-monsters.json")
BACKUP = Path("staging/srd-5.2.1/published-monsters-before-330.json")
REPORT = Path("staging/srd-5.2.1/publication-execution-report.txt")
EXPECTED_SEEDS = {
    "Giant Rat": "cf86b7f1-a610-4ca3-b7f3-7ce2c9c8e111",
    "Goblin Minion": "cf86b7f1-a610-4ca3-b7f3-7ce2c9c8e112",
    "Skeleton": "cf86b7f1-a610-4ca3-b7f3-7ce2c9c8e113",
    "Zombie": "cf86b7f1-a610-4ca3-b7f3-7ce2c9c8e114",
}
def main():
    candidate = json.loads(SOURCE.read_text(encoding="utf-8"))
    existing = json.loads(DEST.read_text(encoding="utf-8"))
    monsters = candidate.get("monsters", [])
    names = [m["name"] for m in monsters]
    ids = [m["id"] for m in monsters]
    current = {m["name"]: m["id"] for m in existing.get("monsters", [])}
    expected = EXPECTED_SEEDS
    problems = []
    if candidate.get("schema_version") != "1.2.0":
        problems.append("Candidate schema must be 1.2.0")
    if len(monsters) != 330 or len(set(names)) != 330 or len(set(ids)) != 330:
        problems.append("Candidate must have 330 unique names and IDs")
    if candidate.get("catalog_version") != "FINAL-REVIEW-ONLY":
        problems.append("Candidate is not the approved final-review artifact")
    if len(current) == 330 and all(
        next((m["id"] for m in monsters if m["name"] == name), None) == old_id
        for name, old_id in expected.items()
    ):
        print("Published catalog already has 330 monsters. No changes made.")
        return
    if current != expected:
        problems.append("Existing published four-monster seed IDs do not match approved baseline")
    by_name = {m["name"]: m for m in monsters}
    if any(by_name.get(name, {}).get("id") != mid for name, mid in expected.items()):
        problems.append("One or more of the four original published IDs changed")
    if sum(m.get("size") == "Medium or Small" for m in monsters) != 36:
        problems.append("36 restored alternative-size descriptions not present")
    if any(m.get("source", {}).get("type") != "official_srd" for m in monsters):
        problems.append("Unexpected monster source type")
    if "Young White Dragon Intelligence saving throw" not in candidate.get("source", {}).get("modifications", ""):
        problems.append("Required Young White Dragon source ambiguity note absent")
    if problems:
        raise SystemExit("PUBLICATION ABORTED:\n" + "\n".join(problems))
    # Validate serializability and backup BEFORE changing the tracked file.
    final = dict(candidate)
    final["catalog_version"] = "SRD-5.2.1-330"
    payload = json.dumps(final, ensure_ascii=False, indent=2) + "\n"
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEST, BACKUP)
    DEST.write_text(payload, encoding="utf-8")
    reloaded = json.loads(DEST.read_text(encoding="utf-8"))
    if len(reloaded["monsters"]) != 330:
        shutil.copy2(BACKUP, DEST)
        raise SystemExit("Readback failed; original published file restored")
    report = [
        "SRD 5.2.1 CATALOG PUBLICATION — LOCAL WORKTREE UPDATED",
        "Published records: 330",
        "Original seed IDs preserved: 4",
        "Restored alternative-size descriptors: 36",
        "Schema: 1.2.0",
        "Tracked file updated: " + str(DEST),
        "Original tracked file backup: " + str(BACKUP),
        "Browser custom monster localStorage untouched.",
        "NOT YET PUSHED TO GITHUB: review, commit and push separately.",
    ]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()
