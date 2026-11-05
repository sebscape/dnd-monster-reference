import { useEffect, useState } from "react";

import { encryptToken, loadSettings, saveSettings, type Settings } from "./artworkSettings";

const DB_NAME = "dnd-monster-reference-artwork-v1";
const STORE = "style-references";
type Reference = { id: string; name: string; data: string; mime: string };
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
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [replaceToken, setReplaceToken] = useState(false);
  const [saving, setSaving] = useState(false);
  const [references, setReferences] = useState<Reference[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { void getReferences().then(setReferences).catch(() => setError("Browser image storage is unavailable.")); }, []);
  async function save() {
    setError(""); setMessage("");
    if (saving) return;
    setSaving(true);
    try {
      const previous = loadSettings();
      let encryptedToken = previous.encryptedToken;
      if (replaceToken || (!previous.encryptedToken && token)) {
        if (!token.trim()) throw new Error("Enter a new API token, or cancel the replacement.");
        if (password.length < 12) throw new Error("Use an encryption password of at least 12 characters.");
        if (password !== confirmation) throw new Error("Encryption passwords do not match.");
        encryptedToken = await encryptToken(token, password);
      }
      const changed = previous.provider !== settings.provider || previous.model !== settings.model || previous.commonPrompt !== settings.commonPrompt || encryptedToken !== previous.encryptedToken;
      const next: Settings = { provider: settings.provider, model: settings.model, commonPrompt: settings.commonPrompt, version: changed ? previous.version + 1 : previous.version, ...(encryptedToken ? { encryptedToken } : {}) };
      saveSettings(next);
      setSettings(next); setToken(""); setPassword(""); setConfirmation(""); setReplaceToken(false);
      setMessage("Artwork settings saved in this browser. Version " + next.version + ". " + (encryptedToken ? "API token stored encrypted." : "No API token configured."));
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save artwork settings."); }
    finally { setSaving(false); }
  }
  function clearToken() {
    if (!window.confirm("Remove the saved encrypted API token? You will need to enter it again to generate artwork.")) return;
    try {
      const current = loadSettings();
      const next: Settings = { ...current, version: current.version + 1 };
      delete next.encryptedToken;
      saveSettings(next);
      setSettings(next); setToken(""); setPassword(""); setConfirmation(""); setReplaceToken(false);
      setMessage("Encrypted API token removed."); setError("");
    } catch { setError("Could not remove the encrypted token."); }
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
      <div><strong>API Token:</strong> {settings.encryptedToken ? "Encrypted token saved" : "Not configured"}</div>
      {settings.encryptedToken && !replaceToken ? <div className="actions"><button type="button" onClick={() => setReplaceToken(true)}>Replace API token / reset password</button><button type="button" onClick={clearToken}>Remove token</button></div> : <>
        <label>{settings.encryptedToken ? "Replacement API Token" : "API Token"}<input type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} placeholder="Enter API token" /></label>
        <label>Encryption password (minimum 12 characters)<input type="password" autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} /></label>
        <label>Confirm encryption password<input type="password" autoComplete="new-password" value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>
        {replaceToken && <button type="button" onClick={() => { setReplaceToken(false); setToken(""); setPassword(""); setConfirmation(""); }}>Cancel token replacement</button>}
      </>}
    </div>
    <p className="muted">The token is encrypted with AES-256-GCM before being saved in this browser. Your encryption password is never saved. If forgotten, replace the token and choose a new password. Encryption protects stored data, but cannot protect an unlocked token from malicious scripts. No generation requests are sent yet.</p>
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
    <div className="actions"><button type="button" disabled={saving} onClick={() => void save()}>{saving ? "Saving…" : "Save artwork settings"}</button><button type="button" onClick={onClose}>Back to monsters</button></div>
  </section>;
}
