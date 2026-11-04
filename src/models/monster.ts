export interface Monster {
  id: string;
  name: string;
  size: string;
  type: string;
  challenge_rating: string;
  armor_class: number;
  hit_points: number;
  initiative_bonus: number;
  tags: string[];
  source: { type: "official_srd" | "third_party" | "homebrew"; name: string; reference?: string };
  derived_from?: { monster_id: string };
  timestamp_created: string;
  timestamp_modified: string;
}
export interface MonsterCatalog {
  schema_version: string;
  catalog_version?: string;
  monsters: Monster[];
}
export function isMonster(value: unknown): value is Monster {
  if (!value || typeof value !== "object") return false;
  const m = value as Partial<Monster>;
  return typeof m.id === "string" && typeof m.name === "string" && typeof m.size === "string" && typeof m.type === "string" && typeof m.challenge_rating === "string" && typeof m.armor_class === "number" && typeof m.hit_points === "number" && typeof m.initiative_bonus === "number" && Array.isArray(m.tags) && !!m.source && typeof m.source.name === "string" && typeof m.timestamp_created === "string" && typeof m.timestamp_modified === "string";
}
