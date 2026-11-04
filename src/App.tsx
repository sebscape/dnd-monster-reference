import { useEffect, useMemo, useState } from "react";
import type { Monster, MonsterCatalog } from "./models/monster";
import { isMonster } from "./models/monster";

const LOCAL_KEY = "dnd-monster-reference-custom-v1";
function readCustom(): Monster[] {
  try {
    const data: unknown = JSON.parse(localStorage.getItem(LOCAL_KEY) ?? "[]");
    return Array.isArray(data) ? data.filter(isMonster) : [];
  } catch { return []; }
}
function downloadJson(name: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export default function App() {
  const [published, setPublished] = useState<Monster[]>([]);
  const [custom, setCustom] = useState<Monster[]>(readCustom);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Monster | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/data/published-monsters.json").then(r => { if (!r.ok) throw new Error("Catalog could not be loaded"); return r.json(); })
      .then((data: MonsterCatalog) => setPublished(Array.isArray(data.monsters) ? data.monsters.filter(isMonster) : []))
      .catch(e => setError(String(e)));
  }, []);
  useEffect(() => { localStorage.setItem(LOCAL_KEY, JSON.stringify(custom)); }, [custom]);
  const monsters = useMemo(() => [...published, ...custom].filter(m =>
    [m.name, m.type, m.challenge_rating, ...m.tags].some(v => v.toLowerCase().includes(query.toLowerCase()))
  ).sort((a,b) => a.name.localeCompare(b.name)), [published, custom, query]);
  function createCustom(base?: Monster) {
    const now = new Date().toISOString();
    const name = window.prompt("Name for custom monster:", base ? base.name + " (Custom)" : "New Monster");
    if (!name?.trim()) return;
    const monster: Monster = {
      id: crypto.randomUUID(), name: name.trim(), size: base?.size ?? "Medium", type: base?.type ?? "Beast",
      challenge_rating: base?.challenge_rating ?? "0", armor_class: base?.armor_class ?? 10,
      hit_points: base?.hit_points ?? 1, initiative_bonus: base?.initiative_bonus ?? 0,
      tags: [...(base?.tags ?? [])], source: { type: "homebrew", name: "Custom" },
      ...(base ? { derived_from: { monster_id: base.id } } : {}), timestamp_created: now, timestamp_modified: now
    };
    setCustom(prev => [...prev, monster]); setSelected(monster);
  }
  async function importCustom(file: File | undefined) {
    if (!file) return;
    try {
      const data: unknown = JSON.parse(await file.text());
      const raw = Array.isArray(data) ? data : (data as MonsterCatalog)?.monsters;
      if (!Array.isArray(raw) || !raw.every(isMonster) || raw.some(m => m.source.type !== "homebrew")) throw new Error("Expected a custom monster catalog");
      const ids = new Set([...published, ...custom].map(m => m.id));
      if (raw.some(m => ids.has(m.id)) || new Set(raw.map(m => m.id)).size !== raw.length) throw new Error("Duplicate monster UUID detected");
      setCustom(prev => [...prev, ...raw]); setError("");
    } catch (e) { setError("Import failed: " + String(e)); }
  }
  return <main>
    <header><div><h1>D&D Monster Reference</h1><p>Published catalog + private custom monsters</p></div><span className="count">{published.length} published · {custom.length} custom</span></header>
    <div className="toolbar"><input aria-label="Search monsters" placeholder="Search name, type, CR, tags…" value={query} onChange={e => setQuery(e.target.value)} />
      <button onClick={() => createCustom()}>+ New custom monster</button>
      <button onClick={() => downloadJson("custom-monsters.json", { schema_version: "1.0.0", monsters: custom })}>Export custom JSON</button>
      <label className="upload">Import custom JSON<input type="file" accept=".json,application/json" onChange={e => { void importCustom(e.target.files?.[0]); e.target.value = ""; }} /></label></div>
    {error && <p role="alert" className="error">{error}</p>}
    <div className="layout"><section className="list"><h2>Monsters</h2>{monsters.length === 0 && <p className="muted">No monsters found. The published catalog is intentionally empty until licensed SRD records are imported. Create a custom monster to begin.</p>}
      {monsters.map(m => <button key={m.id} className={"monster " + (selected?.id === m.id ? "active" : "")} onClick={() => setSelected(m)}><strong>{m.name}</strong><small>{m.type} · CR {m.challenge_rating} · {m.source.type === "homebrew" ? "Custom" : "Published"}</small></button>)}</section>
      <section className="detail">{selected ? <><h2>{selected.name}</h2><p>{selected.size} {selected.type} · Challenge {selected.challenge_rating}</p><div className="stats"><span>AC <b>{selected.armor_class}</b></span><span>HP <b>{selected.hit_points}</b></span><span>Initiative <b>{selected.initiative_bonus >= 0 ? "+" : ""}{selected.initiative_bonus}</b></span></div><p className="muted">UUID: {selected.id}</p><p>Tags: {selected.tags.join(", ") || "None"}</p><p>Source: {selected.source.name}</p>{selected.source.type !== "homebrew" && <button onClick={() => createCustom(selected)}>Create editable copy</button>}{selected.source.type === "homebrew" && <p className="muted">Full custom stat-block editor is next in development.</p>}</> : <p className="muted">Select a monster to inspect its record.</p>}</section></div>
    <footer>Starter milestone · JSON remains the portable source format · Custom records stay in this browser until exported.</footer>
  </main>;
}
