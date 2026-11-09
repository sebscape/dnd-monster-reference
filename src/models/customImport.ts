// Importing a custom-monster JSON file: reading it, finding duplicates of the
// monsters already in the library, and merging with the DM's choices.
import type { Monster, MonsterCatalog } from "./monster";
import { isMonster } from "./monster";

export type ImportMode = "add" | "replace";
export type DuplicateChoice = "keep_original" | "overwrite" | "keep_both";

export interface Duplicate {
  incoming: Monster;
  existing: Monster;
  /** Same UUID (the same monster exported earlier) or just the same name. */
  match: "id" | "name";
}

export interface ImportSummary { added: number; overwritten: number; keptBoth: number; skipped: number; replaced: number }

/** Reads and checks a custom-monster file. Throws a readable error if it can't be imported. */
export function readImportFile(text: string, published: Monster[]): Monster[] {
  let data: unknown;
  try { data = JSON.parse(text); } catch { throw new Error("The file isn't valid JSON."); }
  const raw = Array.isArray(data) ? data : (data as MonsterCatalog | null)?.monsters;
  if (!Array.isArray(raw)) throw new Error("The file doesn't contain a list of monsters.");
  if (!raw.length) throw new Error("The file contains no monsters.");
  const bad = raw.findIndex(m => !isMonster(m));
  if (bad >= 0) throw new Error("Record " + (bad + 1) + " isn't a valid monster.");
  const monsters = raw as Monster[];
  const notCustom = monsters.filter(m => m.source.type !== "homebrew");
  if (notCustom.length) throw new Error("Only custom monsters can be imported; " + notCustom.map(m => m.name).slice(0, 3).join(", ") + (notCustom.length > 3 ? "…" : "") + (notCustom.length === 1 ? " is a published record." : " are published records."));
  const ids = monsters.map(m => m.id);
  if (new Set(ids).size !== ids.length) throw new Error("The file lists the same monster UUID twice.");
  const publishedIds = new Set(published.map(m => m.id));
  if (monsters.some(m => publishedIds.has(m.id))) throw new Error("A monster in the file uses a published monster's UUID.");
  return monsters;
}

const nameKey = (name: string) => name.trim().toLocaleLowerCase();

/** Incoming monsters that are already in the library: same UUID first, otherwise same name. */
export function findDuplicates(existing: Monster[], incoming: Monster[]): Duplicate[] {
  const byId = new Map(existing.map(m => [m.id, m]));
  const byName = new Map<string, Monster>();
  for (const m of existing) if (!byName.has(nameKey(m.name))) byName.set(nameKey(m.name), m);
  const out: Duplicate[] = [];
  for (const m of incoming) {
    const sameId = byId.get(m.id);
    if (sameId) { out.push({ incoming: m, existing: sameId, match: "id" }); continue; }
    const sameName = byName.get(nameKey(m.name));
    if (sameName) out.push({ incoming: m, existing: sameName, match: "name" });
  }
  return out;
}

/** "Goblin Chief" → "Goblin Chief (2)", or (3)… if that's taken too, like copying files in Explorer. */
export function uniqueName(name: string, taken: Set<string>): string {
  const base = name.replace(/ \(\d+\)$/, "");
  for (let n = 2; ; n++) {
    const candidate = base + " (" + n + ")";
    if (!taken.has(nameKey(candidate))) return candidate;
  }
}

/**
 * Adds the incoming monsters to the library. For duplicates (keyed by the incoming UUID):
 * keep_original skips it; overwrite replaces the original but keeps the original's UUID
 * (so its artwork and saved battle-tracker encounters still point at it); keep_both adds
 * it under a new UUID and a numbered name.
 */
export function mergeImport(existing: Monster[], incoming: Monster[], choices: Record<string, DuplicateChoice>, makeId: () => string = () => crypto.randomUUID()): { monsters: Monster[]; summary: ImportSummary } {
  const dupes = new Map(findDuplicates(existing, incoming).map(d => [d.incoming.id, d]));
  const result = [...existing];
  const taken = new Set(existing.map(m => nameKey(m.name)));
  const summary: ImportSummary = { added: 0, overwritten: 0, keptBoth: 0, skipped: 0, replaced: 0 };
  for (const m of incoming) {
    const dup = dupes.get(m.id);
    if (!dup) { result.push(m); taken.add(nameKey(m.name)); summary.added++; continue; }
    const choice = choices[m.id] ?? "keep_original";
    if (choice === "keep_original") { summary.skipped++; continue; }
    if (choice === "overwrite") {
      const i = result.findIndex(x => x.id === dup.existing.id);
      result[i] = { ...m, id: dup.existing.id };
      taken.add(nameKey(m.name));
      summary.overwritten++;
      continue;
    }
    const name = uniqueName(m.name, taken);
    taken.add(nameKey(name));
    result.push({ ...m, id: makeId(), name });
    summary.keptBoth++;
  }
  return { monsters: result, summary };
}

export function describeSummary(s: ImportSummary): string {
  if (s.replaced) return "Replaced your custom monsters with the " + s.replaced + " in the file.";
  const parts = [
    s.added && s.added + " added",
    s.overwritten && s.overwritten + " overwritten",
    s.keptBoth && s.keptBoth + " kept as copies",
    s.skipped && s.skipped + " skipped (kept your originals)",
  ].filter(Boolean);
  return "Import finished: " + (parts.length ? parts.join(", ") : "nothing changed") + ".";
}
