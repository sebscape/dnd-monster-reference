#!/usr/bin/env python3
"""Review extraction artifacts without altering original monster text or catalog."""
import json
import re
from pathlib import Path

ROOT = Path("staging/srd-5.2.1")
SRC = ROOT / "monster-excerpts.json"
OUT = ROOT / "excerpt-cleanup-audit.txt"

def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    records = data["records"]
    issues = []
    counts = {"page_markers": 0, "column_markers": 0, "printed_footers": 0,
              "next_monster_heading": 0, "possible_section_heading": 0}
    for i, rec in enumerate(records):
        raw = rec["raw_excerpt"]
        flags = []
        if "========== PDF PAGE " in raw:
            counts["page_markers"] += 1
            flags.append("page marker")
        if "---------- LEFT ----------" in raw or "---------- RIGHT ----------" in raw:
            counts["column_markers"] += 1
            flags.append("column marker")
        if "System Reference Document 5.2.1" in raw:
            counts["printed_footers"] += 1
            flags.append("printed footer")
        if i + 1 < len(records) and raw.rstrip().endswith("\n" + records[i + 1]["name"]):
            counts["next_monster_heading"] += 1
            flags.append("next monster heading")
        tail = raw.rstrip().splitlines()[-1].strip()
        if (re.fullmatch(r"[A-Z][A-Za-z’' -]{2,55}", tail)
                and tail not in {rec["name"], records[i + 1]["name"] if i + 1 < len(records) else ""}):
            counts["possible_section_heading"] += 1
            flags.append(f"possible section heading: {tail}")
        if flags:
            issues.append((rec["name"], flags))
    lines = [
        f"Excerpts: {len(records)}",
        "REVIEW ONLY — original excerpts and published monsters unchanged.",
        "",
        *[f"{key}: {value}" for key, value in counts.items()],
        "",
        "PER-MONSTER FLAGS:",
        *[f"{name}: {', '.join(flags)}" for name, flags in issues],
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:9]))
    print(f"Report: {OUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
