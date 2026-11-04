import { useEffect, useMemo, useState } from "react";
import type { Monster, MonsterCatalog, NamedFeature } from "./models/monster";
import { ABILITY_KEYS, isMonster, newMonster, SCHEMA_VERSION } from "./models/monster";

const LOCAL_KEY = "dnd-monster-reference-custom-v1";
const FEATURE_KEYS = ["traits", "actions", "bonus_actions", "reactions", "legendary_actions", "spellcasting"] as const;
const TEXT_KEYS = ["alignment", "armor_description", "hit_dice", "speed", "saving_throws", "skills", "damage_vulnerabilities", "damage_resistances", "damage_immunities", "condition_immunities", "senses", "languages"] as const;
function readCustom(): Monster[] {
  try {
    const data: unknown = JSON.parse(localStorage.getItem(LOCAL_KEY) ?? "[]");
    return Array.isArray(data) ? data.filter(isMonster).filter(m => m.source.type === "homebrew") : [];
  } catch { return []; }
}
function downloadJson(name: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const titleCase = (s: string) => s.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
const crValue = (cr: string): number => {
  const text = cr.trim();
  if (/^\d+\/\d+$/.test(text)) {
    const [numerator, denominator] = text.split("/").map(Number);
    return denominator > 0 ? numerator / denominator : NaN;
  }
  return text !== "" && Number.isFinite(Number(text)) ? Number(text) : NaN;
};
const searchableText = (m: Monster): string => [
  m.name, m.size, m.type, m.challenge_rating, m.alignment, m.speed,
  m.saving_throws, m.skills, m.senses, m.languages, m.damage_vulnerabilities,
  m.damage_resistances, m.damage_immunities, m.condition_immunities,
  m.source.name, ...m.tags,
  ...FEATURE_KEYS.flatMap(k => (m[k] ?? []).flatMap(f => [f.name, f.description]))
].filter(Boolean).join(" ").toLocaleLowerCase();
const modifier = (n: number) => { const m = Math.floor((n - 10) / 2); return (m >= 0 ? "+" : "") + m; };
function FeatureEditor({ label, features, onChange }: { label: string; features: NamedFeature[]; onChange: (v: NamedFeature[]) => void }) {
  return <fieldset><legend>{label}</legend>{features.map((f, i) => <div className="feature-edit" key={i}>
    <input aria-label={label + " name " + (i + 1)} placeholder="Feature name" value={f.name} onChange={e => onChange(features.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
    <textarea aria-label={label + " description " + (i + 1)} placeholder="Description and dice notation" value={f.description} onChange={e => onChange(features.map((x, j) => j === i ? { ...x, description: e.target.value } : x))} />
    <button type="button" onClick={() => onChange(features.filter((_, j) => j !== i))}>Remove</button>
  </div>)}<button type="button" onClick={() => onChange([...features, { name: "", description: "" }])}>+ Add {label.toLowerCase().replace(/s$/, "")}</button></fieldset>;
}
function Editor({ initial, onSave, onCancel }: { initial: Monster; onSave: (m: Monster) => void; onCancel: () => void }) {
  const [draft, setDraft] = useState<Monster>(() => structuredClone(initial));
  const [error, setError] = useState("");
  function set<K extends keyof Monster>(key: K, value: Monster[K]) { setDraft(prev => ({ ...prev, [key]: value })); }
  function save(e: React.FormEvent) {
    e.preventDefault();
    const candidate = { ...draft, name: draft.name.trim(), timestamp_modified: new Date().toISOString() };
    if (!candidate.name) { setError("Monster name is required."); return; }
    if (candidate.armor_class < 0 || candidate.hit_points < 1 || !Number.isInteger(candidate.hit_points)) { setError("AC must be nonnegative and HP must be a positive whole number."); return; }
    if (!isMonster(candidate)) { setError("Monster data failed validation."); return; }
    onSave(candidate);
  }
  return <form onSubmit={save} className="editor"><div className="editor-heading"><h2>{initial.name ? "Edit custom monster" : "New custom monster"}</h2><button type="button" onClick={onCancel}>Cancel</button></div>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="fields">
      <label>Name<input required value={draft.name} onChange={e => set("name", e.target.value)} /></label>
      <label>Size<input value={draft.size} onChange={e => set("size", e.target.value)} /></label>
      <label>Type<input value={draft.type} onChange={e => set("type", e.target.value)} /></label>
      <label>Challenge rating<input value={draft.challenge_rating} onChange={e => set("challenge_rating", e.target.value)} /></label>
      <label>Armor class<input type="number" min="0" value={draft.armor_class} onChange={e => set("armor_class", Number(e.target.value))} /></label>
      <label>Hit points<input type="number" min="1" value={draft.hit_points} onChange={e => set("hit_points", Number(e.target.value))} /></label>
      <label>Initiative bonus<input type="number" value={draft.initiative_bonus} onChange={e => set("initiative_bonus", Number(e.target.value))} /></label>
      <label>Proficiency bonus<input type="number" value={draft.proficiency_bonus ?? ""} onChange={e => set("proficiency_bonus", e.target.value === "" ? undefined : Number(e.target.value))} /></label>
      {TEXT_KEYS.map(k => <label key={k}>{titleCase(k)}<input value={draft[k] ?? ""} onChange={e => set(k, e.target.value)} /></label>)}
    </div>
    <fieldset><legend>Ability scores</legend><div className="abilities">{ABILITY_KEYS.map(k => <label key={k}>{k.toUpperCase()}<input type="number" min="1" max="30" value={draft.abilities?.[k] ?? 10} onChange={e => set("abilities", { ...(draft.abilities ?? { str:10,dex:10,con:10,int:10,wis:10,cha:10 }), [k]: Number(e.target.value) })} /></label>)}</div></fieldset>
    <label>Tags (comma-separated)<input value={draft.tags.join(", ")} onChange={e => set("tags", e.target.value.split(",").map(x => x.trim()).filter(Boolean))} /></label>
    {FEATURE_KEYS.map(k => <FeatureEditor key={k} label={titleCase(k)} features={draft[k] ?? []} onChange={v => set(k, v)} />)}
    <div className="actions"><button type="submit">Save custom monster</button><button type="button" onClick={onCancel}>Cancel</button></div>
  </form>;
}
function Detail({ monster, onEdit, onCopy, onDelete }: { monster: Monster; onEdit: () => void; onCopy: () => void; onDelete: () => void }) {
  const custom = monster.source.type === "homebrew";
  return <><h2>{monster.name}</h2><p>{monster.size} {monster.type} · CR {monster.challenge_rating} · {custom ? "Custom" : "Published"}</p>
    <div className="stats"><span>AC <b>{monster.armor_class}</b></span><span>HP <b>{monster.hit_points}</b></span><span>Initiative <b>{monster.initiative_bonus >= 0 ? "+" : ""}{monster.initiative_bonus}</b></span></div>
    {monster.speed && <p><b>Speed:</b> {monster.speed}</p>}
    {monster.abilities && <div className="abilities ability-display">{ABILITY_KEYS.map(k => <div key={k}><b>{k.toUpperCase()}</b><span>{monster.abilities![k]} ({modifier(monster.abilities![k])})</span></div>)}</div>}
    {TEXT_KEYS.filter(k => k !== "speed").map(k => monster[k] ? <p key={k}><b>{titleCase(k)}:</b> {monster[k]}</p> : null)}
    {FEATURE_KEYS.map(k => (monster[k]?.length ?? 0) > 0 && <section key={k}><h3>{titleCase(k)}</h3>{monster[k]?.map((f, i) => <p key={i}><b>{f.name}.</b> {f.description}</p>)}</section>)}
    <p><b>Tags:</b> {monster.tags.join(", ") || "None"}</p><p><b>Source:</b> {monster.source.name}</p>
    <p className="muted">UUID: {monster.id}</p>
    <div className="actions">{custom ? <><button onClick={onEdit}>Edit</button><button className="danger" onClick={onDelete}>Delete</button></> : <button onClick={onCopy}>Create editable copy</button>}</div>
  </>;
}
export default function App() {
  const [published, setPublished] = useState<Monster[]>([]);
  const [custom, setCustom] = useState<Monster[]>(readCustom);
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [tagFilter, setTagFilter] = useState("all");
  const [minCr, setMinCr] = useState("");
  const [maxCr, setMaxCr] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState<Monster | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/data/published-monsters.json").then(r => { if (!r.ok) throw new Error("Catalog could not be loaded"); return r.json(); })
      .then((data: MonsterCatalog) => setPublished(Array.isArray(data.monsters) ? data.monsters.filter(isMonster) : []))
      .catch(e => setError(String(e)));
  }, []);
  useEffect(() => { try { localStorage.setItem(LOCAL_KEY, JSON.stringify(custom)); } catch { setError("Local save failed. Export your custom JSON backup immediately."); } }, [custom]);
  const allMonsters = useMemo(() => [...published, ...custom], [published, custom]);
  const types = useMemo(() => [...new Set(allMonsters.map(m => m.type))].sort((a, b) => a.localeCompare(b)), [allMonsters]);
  const tags = useMemo(() => [...new Set(allMonsters.flatMap(m => m.tags))].sort((a, b) => a.localeCompare(b)), [allMonsters]);
  const monsters = useMemo(() => allMonsters.filter(m => {
    if (sourceFilter === "published" && m.source.type === "homebrew") return false;
    if (sourceFilter === "custom" && m.source.type !== "homebrew") return false;
    if (typeFilter !== "all" && m.type !== typeFilter) return false;
    if (tagFilter !== "all" && !m.tags.includes(tagFilter)) return false;
    const cr = crValue(m.challenge_rating);
    if (minCr !== "" && !(cr >= crValue(minCr))) return false;
    if (maxCr !== "" && !(cr <= crValue(maxCr))) return false;
    const words = query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    return words.every(word => searchableText(m).includes(word));
  }).sort((a,b) => a.name.localeCompare(b.name)),
  [allMonsters, sourceFilter, typeFilter, tagFilter, minCr, maxCr, query]);
  const filtersActive = Boolean(query || sourceFilter !== "all" || typeFilter !== "all" || tagFilter !== "all" || minCr || maxCr);
  function resetFilters() {
    setQuery(""); setSourceFilter("all"); setTypeFilter("all");
    setTagFilter("all"); setMinCr(""); setMaxCr("");
  }
  const selected = allMonsters.find(m => m.id === selectedId) ?? null;
  function saveCustom(monster: Monster) {
    setCustom(prev => prev.some(m => m.id === monster.id) ? prev.map(m => m.id === monster.id ? monster : m) : [...prev, monster]);
    setSelectedId(monster.id); setEditing(null); setError("");
  }
  function deleteCustom(monster: Monster) {
    if (!window.confirm("Delete " + monster.name + "? Export a backup first if you want to keep it.")) return;
    setCustom(prev => prev.filter(m => m.id !== monster.id)); setSelectedId(null);
  }
  async function importCustom(file: File | undefined) {
    if (!file) return;
    try {
      const data: unknown = JSON.parse(await file.text());
      const raw = Array.isArray(data) ? data : (data as MonsterCatalog)?.monsters;
      if (!Array.isArray(raw) || !raw.every(isMonster) || raw.some(m => m.source.type !== "homebrew")) throw new Error("Expected a valid custom monster catalog");
      const ids = new Set([...published, ...custom].map(m => m.id));
      if (raw.some(m => ids.has(m.id)) || new Set(raw.map(m => m.id)).size !== raw.length) throw new Error("Duplicate monster UUID detected; no records imported");
      setCustom(prev => [...prev, ...raw]); setError("");
    } catch (e) { setError("Import failed: " + String(e)); }
  }
  return <main>
    <header><div><h1>D&D Monster Reference</h1><p>Published catalog + private custom monsters</p></div><span className="count">{published.length} published · {custom.length} custom</span></header>
    <div className="toolbar"><input aria-label="Search monsters" placeholder="Search name, type, CR, tags…" value={query} onChange={e => setQuery(e.target.value)} />
      <button onClick={() => setEditing(newMonster())}>+ New custom monster</button>
      <button onClick={() => downloadJson("custom-monsters.json", { schema_version: SCHEMA_VERSION, monsters: custom })}>Export custom JSON</button>
      <label className="upload">Import custom JSON<input type="file" accept=".json,application/json" onChange={e => { void importCustom(e.target.files?.[0]); e.target.value = ""; }} /></label></div>
    <section className="filter-panel" aria-label="Monster filters">
      <div className="filter-fields">
        <label>Source<select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}><option value="all">All sources</option><option value="published">Published</option><option value="custom">Custom</option></select></label>
        <label>Creature type<select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}><option value="all">All types</option>{types.map(t => <option key={t} value={t}>{t}</option>)}</select></label>
        <label>Tag<select value={tagFilter} onChange={e => setTagFilter(e.target.value)}><option value="all">All tags</option>{tags.map(t => <option key={t} value={t}>{t}</option>)}</select></label>
        <label>Minimum CR<input aria-label="Minimum challenge rating" placeholder="e.g. 1/8" value={minCr} onChange={e => setMinCr(e.target.value)} /></label>
        <label>Maximum CR<input aria-label="Maximum challenge rating" placeholder="e.g. 2" value={maxCr} onChange={e => setMaxCr(e.target.value)} /></label>
      </div>
      <div className="filter-summary"><span role="status">Showing <strong>{monsters.length}</strong> of <strong>{allMonsters.length}</strong> monsters</span><button type="button" disabled={!filtersActive} onClick={resetFilters}>Reset filters</button></div>
    </section>
    {error && <p role="alert" className="error">{error}</p>}
    <div className="layout"><section className="list"><h2>Monsters</h2>{monsters.length === 0 && <p className="muted">{allMonsters.length === 0 ? "No monsters in the catalog. Create a custom monster to begin." : "No monsters match the current filters."}</p>}
      {monsters.map(m => <button key={m.id} className={"monster " + (selectedId === m.id ? "active" : "")} onClick={() => { setSelectedId(m.id); setEditing(null); }}><strong>{m.name}</strong><small>{m.type} · CR {m.challenge_rating} · {m.source.type === "homebrew" ? "Custom" : "Published"}</small></button>)}</section>
      <section className="detail">{editing ? <Editor key={editing.id} initial={editing} onSave={saveCustom} onCancel={() => setEditing(null)} /> : selected ? <Detail monster={selected} onEdit={() => setEditing(selected)} onCopy={() => setEditing(newMonster(selected))} onDelete={() => deleteCustom(selected)} /> : <p className="muted">Select a monster to inspect its record, or create a custom monster.</p>}</section></div>
    <footer>Custom records are saved in this browser. Export custom JSON regularly for backup. Published definitions remain read-only.</footer>
  </main>;
}
