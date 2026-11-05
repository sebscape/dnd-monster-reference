import { useEffect, useState } from "react";

const SETTINGS_KEY = "dnd-monster-reference-artwork-settings-v1";
const DB_NAME = "dnd-monster-reference-artwork-v1";
const STORE = "style-references";
const DEFAULT_PROMPT = "Create an original fantasy bestiary illustration of the specified creature. Show the entire creature with a clear silhouette, consistent lighting and brushwork, and a true transparent background. No text, labels, scenery, or borders.";
type Settings = { provider: string; model: string; commonPrompt: string; version: number };
type Reference = { id: string; name: string; data: string; mime: string };
const defaults: Settings = { provider: "OpenAI", model: "", commonPrompt: DEFAULT_PROMPT, version: 1 };
function loadSettings(): Settings {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? "null");
    if (parsed && typeof parsed === "object") {
      const p = parsed as Partial<Settings>;
      if (typeof p.commonPrompt === "string" && typeof p.provider === "string")
        return { provider: p.provider, model: typeof p.model === "string" ? p.model : "", commonPrompt: p.commonPrompt, version: Number.isInteger(p.version) ? p.version! : 1 };
    }
  } catch { /* fall back to defaults */ }
  return defaults;
}
function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => { if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE, { keyPath: "id" }); };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function getReferences(): Promise<Reference[]> {
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result as Reference[]);
      req.onerror = () => reject(req.error);
    });
  } finally { db.close(); }
}
async function putReference(ref: Reference): Promise<void> {
  const db = await database();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(ref);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally { db.close(); }
}
async function removeReference(id: string): Promise<void> {
  const db = await database();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally { db.close(); }
}
function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
export default function ArtworkConfiguration({ onClose }: { onClose: () => void }) {
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [token, setToken] = useState("");
  const [references, setReferences] = useState<Reference[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { void getReferences().then(setReferences).catch(() => setError("Browser image storage is unavailable.")); }, []);
  function save() {
    try {
      const previous = loadSettings();
      const changed = previous.provider !== settings.provider || previous.model !== settings.model || previous.commonPrompt !== settings.commonPrompt;
      const next = { ...settings, version: changed ? previous.version + 1 : previous.version };
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
      setSettings(next);
      setError("");
      setMessage("Artwork settings saved in this browser. Version " + next.version + ". API token was not saved.");
    } catch { setError("Could not save artwork settings in this browser."); }
  }
  async function addFiles(files: FileList | null) {
    if (!files) return;
    setError(""); setMessage("");
    for (const file of Array.from(files)) {
      if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 5 * 1024 * 1024) {
        setError("Use PNG, JPEG or WebP files up to 5 MB each."); return;
      }
      try { await putReference({ id: crypto.randomUUID(), name: file.name, data: await readAsDataUrl(file), mime: file.type }); }
      catch { setError("Could not save reference image. Check browser storage."); return; }
    }
    setReferences(await getReferences());
    setMessage("Reference images saved privately in this browser.");
  }
  async function remove(id: string) {
    try { await removeReference(id); setReferences(await getReferences()); }
    catch { setError("Could not remove reference image."); }
  }
  return <section aria-label="App Configuration" className="detail">
    <div className="editor-heading"><h2>App Configuration — AI Artwork</h2><button type="button" onClick={onClose}>Close</button></div>
    <p className="muted">Configure artwork generation preferences. No image generation requests are sent in this version.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {message && <p role="status">{message}</p>}
    <div className="fields">
      <label>AI Provider<select value={settings.provider} onChange={e => setSettings(s => ({ ...s, provider: e.target.value }))}><option value="OpenAI">OpenAI</option><option value="Other">Other (future integration)</option></select></label>
      <label>Image model (optional)<input value={settings.model} placeholder="Configured when API integration is added" onChange={e => setSettings(s => ({ ...s, model: e.target.value }))} /></label>
      <label>API Token (session only; not stored)<input type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} placeholder="Do not enter a real key until secure integration exists" /></label>
    </div>
    <p className="muted">Security: Browser-only applications cannot safely hide an API token. This field is temporary and is never saved or transmitted. A secure server-side proxy is required before enabling generation.</p>
    <label style={{ display: "block" }}>Common Prompt for Image<textarea style={{ display: "block", width: "100%", minHeight: 150, marginTop: 8 }} value={settings.commonPrompt} onChange={e => setSettings(s => ({ ...s, commonPrompt: e.target.value }))} /></label>
    <p className="muted">This prompt will precede the monster-specific description. Current saved settings version: {settings.version}.</p>
    <fieldset><legend>Style reference images</legend>
      <label className="upload">Add reference images<input type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={e => { void addFiles(e.target.files); e.target.value = ""; }} /></label>
      <p className="muted">Images are kept in this browser's IndexedDB, not uploaded to GitHub. They will be sent only when a future generation request is explicitly initiated.</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
        {references.map(ref => <div key={ref.id} style={{ width: 145 }}><img src={ref.data} alt={"Style reference " + ref.name} style={{ width: "100%", height: 145, objectFit: "contain" }} /><p style={{ overflowWrap: "anywhere" }}>{ref.name}</p><button type="button" onClick={() => void remove(ref.id)}>Remove</button></div>)}
      </div>
      {references.length === 0 && <p className="muted">No reference images added.</p>}
    </fieldset>
    <div className="actions"><button type="button" onClick={save}>Save artwork settings</button><button type="button" onClick={onClose}>Back to monsters</button></div>
  </section>;
}
