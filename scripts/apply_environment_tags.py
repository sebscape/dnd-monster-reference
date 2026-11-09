#!/usr/bin/env python3
"""Copy reviewed environment tags from data/environment-tags.csv into the published catalog.

The SRD 5.2.1 has no habitat or environment data. These tags were written for this
project and reviewed by the owner. They go into each monster's `tags` field, which
both apps already support (the reference app's Tag filter, the battle tracker's
encounter generator). Tags that aren't environment names are left untouched.

Usage:  python3 scripts/apply_environment_tags.py [--check]
  --check  only report what would change; don't write.
"""
import csv
import json
import sys
from pathlib import Path

ENVIRONMENTS = ["Arctic", "Coastal", "Desert", "Forest", "Grassland", "Hill",
                "Mountain", "Swamp", "Underdark", "Underwater", "Urban", "Planar"]
ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "environment-tags.csv"
CATALOG = ROOT / "public" / "data" / "published-monsters.json"
NOTE = " Environment tags in the tags field were added by this project; they are not part of the SRD."


def main() -> int:
    check = "--check" in sys.argv[1:]
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    by_id = {m["id"]: m for m in data["monsters"]}
    problems, changed = [], 0
    seen = set()
    for n, row in enumerate(rows, start=2):
        mid = row["id"].strip()
        if mid in seen:
            problems.append(f"line {n}: {row['name']} appears twice")
        seen.add(mid)
        monster = by_id.get(mid)
        if monster is None:
            problems.append(f"line {n}: no monster with id {mid} ({row['name']})")
            continue
        envs = [e.strip() for e in row["environments"].replace(",", ";").split(";") if e.strip()]
        unknown = [e for e in envs if e not in ENVIRONMENTS]
        if unknown:
            problems.append(f"line {n}: {row['name']}: unknown environment(s) {unknown}; use {', '.join(ENVIRONMENTS)}")
            continue
        if not envs:
            problems.append(f"line {n}: {row['name']}: no environments")
            continue
        others = [t for t in monster.get("tags", []) if t not in ENVIRONMENTS]
        new_tags = others + sorted(set(envs), key=ENVIRONMENTS.index)
        if new_tags != monster.get("tags", []):
            monster["tags"] = new_tags
            changed += 1
    untagged = [m["name"] for m in data["monsters"] if m["id"] not in seen]
    if untagged:
        problems.append(f"{len(untagged)} monsters missing from the CSV: {', '.join(untagged[:10])}")
    if problems:
        print("Not applied — fix these first:", *problems, sep="\n  ")
        return 1
    if NOTE.strip() not in data["source"].get("modifications", ""):
        data["source"]["modifications"] = data["source"].get("modifications", "") + NOTE
    print(f"{changed} monsters {'would change' if check else 'updated'}.")
    if not check:
        CATALOG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
