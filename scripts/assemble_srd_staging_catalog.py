#!/usr/bin/env python3
"""Assemble a REVIEW-ONLY SRD catalog in staging, never in public/data.

Unresolved records are excluded and reported rather than guessed.
"""
import json
import re
import uuid
from pathlib import Path
from parse_pilot_headers import parse as parse_header
from parse_pilot_abilities import parse_abilities
from parse_pilot_secondary_stats import parse_secondary
from parse_pilot_features import parse as parse_features
from audit_immunity_classification import classify
from preview_hyphenation_normalization import CANDIDATE, LINE_JOIN, KEEP_HYPHEN

ROOT = Path("staging/srd-5.2.1")
OUTPUT = ROOT / "assembled-monsters-review.json"
REPORT = ROOT / "assembly-review-report.txt"
SOURCE = ROOT / "monster-excerpts-cleaned.json"
CANDIDATES = ROOT / "hyphenation-candidates-report.txt"
NAMESPACE = uuid.UUID("df7a48e0-f2bf-4b32-b6f7-612accd63920")
STAMP = "2026-11-04T00:00:00.000Z"
SOURCE_INFO = {"type": "official_srd", "name": "System Reference Document 5.2.1",
               "reference": "https://www.dndbeyond.com/srd", "license": "CC BY 4.0"}
DESCRIPTOR = re.compile(r"^(Gargantuan|Huge|Large|Medium|Small|Tiny)(?: or (?:Small|Medium))?\s+(.+),\s+(Lawful Good|Neutral Good|Chaotic Good|Lawful Neutral|Neutral Evil|Chaotic Neutral|Lawful Evil|Chaotic Evil|Unaligned|Neutral)$")
ABILITY_NAMES = ("str", "dex", "con", "int", "wis", "cha")
FEATURE_MAP = {"Traits":"traits", "Actions":"actions", "Bonus Actions":"bonus_actions",
               "Reactions":"reactions", "Legendary Actions":"legendary_actions"}

def normalizer():
    candidates = CANDIDATE.findall(CANDIDATES.read_text(encoding="utf-8"))
    if len(candidates) != 177:
        raise SystemExit(f"Expected 177 reviewed hyphenation patterns, got {len(candidates)}")
    approved = {}
    for left, right, proposed, count in candidates:
        if proposed != left + right:
            raise SystemExit(f"Unreviewed join proposal: {left}-{right}")
        if f"{left}-{right}" not in KEEP_HYPHEN:
            approved[(left, right)] = proposed
    def normalize(value):
        unknown = []
        def sub(match):
            left, right = match.groups()
            if f"{left}-{right}" in KEEP_HYPHEN:
                return left + "-" + right
            if (left, right) in approved:
                return approved[(left, right)]
            unknown.append(f"{left}-{right}")
            return match.group(0)
        return LINE_JOIN.sub(sub, value), unknown
    return normalize

def assemble(record, normalize):
    name = record["name"]
    raw, unknown_joins = normalize(record["cleaned_excerpt"])
    if unknown_joins:
        raise ValueError("Unreviewed hyphenation: " + ", ".join(unknown_joins))
    record = dict(record, cleaned_excerpt=raw)
    header = parse_header(record)
    abilities, ability_notes = parse_abilities(record)
    # SRD 5.2.1 printed page 340 shows Young White Dragon Int 6,
    # modifier -2, and unsigned save "2". Treat +2 as an explicitly
    # documented editorial interpretation, never as verified source text.
    # Require the exact source row before applying this staging-only override.
    if name == "Young White Dragon":
        lines = raw.splitlines()
        int_rows = [i for i, line in enumerate(lines) if re.match(r"^Int\s+6\b", line.strip())]
        if len(int_rows) != 1:
            raise ValueError("Young White Dragon Int source row changed; manual review required")
        i = int_rows[0]
        source_window = " ".join(line.strip() for line in lines[i:i+3]).replace("−", "-").replace("–", "-")
        if not re.search(r"Int\s+6\s+-2\s+2(?:\s|$)", source_window):
            raise ValueError("Young White Dragon unsigned save source pattern changed; manual review required: " + repr(source_window))
        abilities["int"] = {"score": 6, "modifier": -2, "save": 2}
        ability_notes = [note for note in ability_notes if not (note.startswith("Int:") or note == "Missing abilities: Int")]
        if ability_notes:
            raise ValueError("Young White Dragon has additional ability issues: " + "; ".join(ability_notes))
    secondary, secondary_notes = parse_secondary(record)
    sections, preambles, feature_notes = parse_features(record)
    notes = ability_notes + secondary_notes + feature_notes
    if notes:
        raise ValueError("; ".join(notes))
    if len(abilities) != 6:
        raise ValueError(f"Only {len(abilities)} abilities parsed")
    match = DESCRIPTOR.fullmatch(header["descriptor"])
    if not match:
        raise ValueError(f"Unparsed descriptor: {header['descriptor']!r}")
    missing = [k for k in ("size", "ac", "hp", "initiative", "cr", "pb", "speed") if header[k] is None]
    if missing:
        raise ValueError("Missing fields: " + ", ".join(missing))
    size, creature_type, alignment = match.groups()
    monster = {
        "id": str(uuid.uuid5(NAMESPACE, "srd-5.2.1:" + name)),
        "name": name, "size": size, "type": creature_type, "alignment": alignment,
        "challenge_rating": header["cr"], "proficiency_bonus": int(header["pb"]),
        "armor_class": int(header["ac"]), "hit_points": int(header["hp"]),
        "initiative_bonus": int(header["initiative"]), "speed": header["speed"],
        "abilities": {k: abilities[k]["score"] for k in ABILITY_NAMES},
        "tags": [], "source": SOURCE_INFO,
        "timestamp_created": STAMP, "timestamp_modified": STAMP,
    }
    if header["hit_dice"]:
        monster["hit_dice"] = header["hit_dice"]
    ac_line = next((line.strip() for line in raw.splitlines() if line.strip().startswith("AC ")), "")
    if ac_line:
        armor_description = re.match(r"^AC\s+\d+\s*(.*)$", ac_line)
        if armor_description and armor_description.group(1).strip():
            monster["armor_description"] = armor_description.group(1).strip()
    # All six SRD save values are present; only non-default saves are recorded.
    saves = []
    for k in ABILITY_NAMES:
        entry = abilities[k]
        if entry["save"] != entry["modifier"]:
            saves.append(k.title() + " " + f"{entry['save']:+d}")
    if saves:
        monster["saving_throws"] = ", ".join(saves)
    for source, target in (
        ("Skills","skills"), ("Senses","senses"), ("Languages","languages"),
        ("Vulnerabilities","damage_vulnerabilities"),
        ("Resistances","damage_resistances"), ("Gear","gear")):
        if source in secondary:
            monster[target] = secondary[source]
    if "Immunities" in secondary:
        damage, conditions, unknown = classify(secondary["Immunities"])
        if unknown:
            raise ValueError("Unknown immunity types: " + repr(unknown))
        if damage:
            monster["damage_immunities"] = ", ".join(damage)
        if conditions:
            monster["condition_immunities"] = ", ".join(conditions)
    for section, features in sections.items():
        monster[FEATURE_MAP[section]] = features
    if "Legendary Actions" in preambles:
        monster["legendary_actions_intro"] = preambles["Legendary Actions"]
    return monster

def main():
    records = json.loads(SOURCE.read_text(encoding="utf-8"))["records"]
    if len(records) != 330:
        raise SystemExit(f"Expected 330 records, got {len(records)}")
    normalize = normalizer()
    built, excluded = [], []
    for record in records:
        try:
            built.append(assemble(record, normalize))
        except (ValueError, KeyError, TypeError) as exc:
            excluded.append((record["name"], str(exc)))
    ids = [monster["id"] for monster in built]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate official UUIDs: aborting")
    catalog = {"schema_version": "1.2.0", "catalog_version": "STAGING-REVIEW-ONLY",
               "monsters": built}
    OUTPUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["SRD STAGING CATALOG ASSEMBLY — NOT FOR PUBLICATION",
             f"Source monsters: {len(records)}", f"Staged records: {len(built)}",
             f"Excluded for review: {len(excluded)}", "",
             "EXCLUDED MONSTERS:"]
    lines.extend(f"  {name}: {reason}" for name, reason in excluded)
    if not excluded:
        lines.append("  none")
    lines += ["", "DOCUMENTED SOURCE INTERPRETATION:",
              "Young White Dragon (SRD 5.2.1 printed page 340): Int 6, modifier -2, save printed as unsigned 2.",
              "Staging interprets the unsigned save as +2; this is an editorial interpretation, NOT a signed value in the PDF.",
              "The source pattern is checked explicitly; unexpected changes stop assembly for this monster.",
              "", "IMPORTANT: this is a structural assembly, not a verified transcription.",
              "Check source stat blocks, saving throws, armor text, spellcasting, and feature rendering.",
              "Published and custom catalogs were not modified."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Staged records: {len(built)}; excluded: {len(excluded)}")
    print(f"Report: {REPORT}")
    print(f"Review JSON: {OUTPUT}")
    print("No published or custom monsters were modified.")

if __name__ == "__main__":
    main()
