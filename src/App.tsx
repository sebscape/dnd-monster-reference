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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState<Monster | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/data/published-monsters.json").then(r => { if (!r.ok) throw new Error("Catalog could not be loaded"); return r.json(); })
      .then((data: MonsterCatalog) => setPublished(Array.isArray(data.monsters) ? data.monsters.filter(isMonster) : []))
      .catch(e => setError(String(e)));
  }, []);
  useEffect(() => { try { localStorage.setItem(LOCAL_KEY, JSON.stringify(custom)); } catch { setError("Local save failed. Export your custom JSON backup immediately."); } }, [custom]);
  const monsters = useMemo(() => [...published, ...custom].filter(m =>
    [m.name, m.type, m.challenge_rating, ...m.tags].some(v => v.toLowerCase().includes(query.toLowerCase()))
  ).sort((a,b) => a.name.localeCompare(b.name)), [published, custom, query]);
  const selected = [...published, ...custom].find(m => m.id === selectedId) ?? null;
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
    {error && <p role="alert" className="error">{error}</p>}
    <div className="layout"><section className="list"><h2>Monsters</h2>{monsters.length === 0 && <p className="muted">No monsters found. The published catalog is intentionally empty until licensed SRD records are imported. Create a custom monster to begin.</p>}
      {monsters.map(m => <button key={m.id} className={"monster " + (selectedId === m.id ? "active" : "")} onClick={() => { setSelectedId(m.id); setEditing(null); }}><strong>{m.name}</strong><small>{m.type} · CR {m.challenge_rating} · {m.source.type === "homebrew" ? "Custom" : "Published"}</small></button>)}</section>
      <section className="detail">{editing ? <Editor key={editing.id} initial={editing} onSave={saveCustom} onCancel={() => setEditing(null)} /> : selected ? <Detail monster={selected} onEdit={() => setEditing(selected)} onCopy={() => setEditing(newMonster(selected))} onDelete={() => deleteCustom(selected)} /> : <p className="muted">Select a monster to inspect its record, or create a custom monster.</p>}</section></div>
    <footer>Custom records are saved in this browser. Export custom JSON regularly for backup. Published definitions remain read-only.</footer>
  </main>;
}
