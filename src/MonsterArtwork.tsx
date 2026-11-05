import { useEffect, useState } from "react";
import type { Monster } from "./models/monster";
import { decryptToken, loadSettings } from "./artworkSettings";

const DB = "dnd-monster-reference-approved-artwork-v1";
const STORE = "images";
type Stored = { monsterId: string; dataUrl: string; approvedAt: string };
function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => { if (!req.result.objectStoreNames.contains(STORE)) req.result.createObjectStore(STORE, { keyPath: "monsterId" }); };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function readImage(monsterId: string): Promise<Stored | undefined> {
  const db = await openDb();
  try { return await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).get(monsterId);
    req.onsuccess = () => resolve(req.result as Stored | undefined);
    req.onerror = () => reject(req.error);
  }); } finally { db.close(); }
}
async function saveImage(image: Stored): Promise<void> {
  const db = await openDb();
  try { await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(image);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  }); } finally { db.close(); }
}
function fileData(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
async function loadReferences(): Promise<string[]> {
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const req = indexedDB.open("dnd-monster-reference-artwork-v1", 1);
    req.onupgradeneeded = () => { if (!req.result.objectStoreNames.contains("style-references")) req.result.createObjectStore("style-references", { keyPath: "id" }); };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  try {
    return await new Promise((resolve, reject) => {
      const req = db.transaction("style-references", "readonly").objectStore("style-references").getAll();
      req.onsuccess = () => resolve((req.result as { data: string }[]).slice(0, 4).map(r => r.data));
      req.onerror = () => reject(req.error);
    });
  } finally { db.close(); }
}
const VISUAL_DESCRIPTIONS: Record<string, string> = {
  aboleth: "An ancient, terrifying aquatic aberration: a huge elongated fishlike body, three vertically arranged eyes, a broad tooth-filled mouth, long grasping tentacles, ridged fins, and slick mucus-coated skin. Pose the entire body and tentacles in a readable vertical composition.",
};
export function monsterPrompt(monster: Monster, extra: string): string {
  const settings = loadSettings();
  const curated = VISUAL_DESCRIPTIONS[monster.name.trim().toLowerCase()];
  const visualDescription = curated ?? [
    "Depict a recognizable " + monster.name + ", a " + monster.size.toLowerCase() + " " + monster.type.toLowerCase() + " fantasy creature.",
    "Use distinctive physical features associated with this creature, emphasizing silhouette, anatomy, textures, and a clear miniature-friendly pose.",
    "Do not depict game rules, statistics, text, symbols, or magical effects unless they are essential to the creature's visible appearance."
  ].join(" ");
  return [
    settings.commonPrompt,
    "Creature: " + monster.name,
    "Visual description: " + visualDescription,
    "Composition: Show the entire creature, including all limbs, fins, tail, and tentacles, inside a vertical 1:2 portrait frame. Keep a true transparent background, with no scenery, lettering, border, or cropped extremities.",
    extra.trim()
  ].filter(Boolean).join("\n\n");
}
export default function MonsterArtwork({ monster, publishedUrl }: { monster: Monster; publishedUrl?: string }) {
  const [approved, setApproved] = useState<Stored>();
  const [candidate, setCandidate] = useState<string | null>(null);
  const [prompt, setPrompt] = useState(() => monsterPrompt(monster, ""));
  const [showPrompt, setShowPrompt] = useState(false);
  const [mode, setMode] = useState<"upload" | "ai">("upload");
  const [unlockPassword, setUnlockPassword] = useState("");
  const [unlockedToken, setUnlockedToken] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    setApproved(undefined); setCandidate(null); setPrompt(monsterPrompt(monster, "")); setError(""); setNotice(""); setShowPrompt(false); setMode("upload");
    void readImage(monster.id).then(v => { if (active) setApproved(v); }).catch(() => { if (active) setError("Could not load local approved artwork."); });
    return () => { active = false; };
  }, [monster.id]);
  async function previewFile(file: File | undefined) {
    if (!file) return;
    setError(""); setNotice("");
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 8 * 1024 * 1024) {
      setError("Choose a PNG, JPEG or WebP image up to 8 MB."); return;
    }
    try { setCandidate(await fileData(file)); }
    catch { setError("Could not read image."); }
  }
  async function generate() {
    if (generating) return;
    if (!prompt.trim()) { setError("Enter an image prompt before generating."); return; }
    setError(""); setNotice("");
    const settings = loadSettings();
    if (settings.provider !== "OpenAI") { setError("Select OpenAI in App Configuration."); return; }
    if (!settings.encryptedToken) { setError("Configure an encrypted API token first."); return; }
    setGenerating(true);
    try {
      const token = unlockedToken ?? await decryptToken(settings.encryptedToken, unlockPassword);
      if (!unlockedToken) { setUnlockedToken(token); setUnlockPassword(""); }
      const refs = await loadReferences();
      const response = await fetch("/.netlify/functions/generate-artwork", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, model: settings.model.trim() || "gpt-image-1.5", prompt, references: refs })
      });
      const result: { image?: string; error?: string } = await response.json().catch(() => ({ error: "Generation service returned an unexpected response. On localhost, use Netlify Dev or the deployed site." }));
      if (!response.ok || !result.image?.startsWith("data:image/png;base64,")) throw new Error(result.error || "Image generation failed.");
      setCandidate(result.image);
      setNotice("AI image generated. Review it before approving; each generation may incur an API charge.");
    } catch (e) {
      if (e instanceof DOMException && e.name === "OperationError") setError("Incorrect encryption password. Try again.");
      else setError(e instanceof Error ? e.message : "Image generation failed.");
    } finally { setGenerating(false); }
  }
  async function approve() {
    if (!candidate) return;
    try {
      const record = { monsterId: monster.id, dataUrl: candidate, approvedAt: new Date().toISOString() };
      await saveImage(record);
      setApproved(record); setCandidate(null); setShowPrompt(false); setNotice(""); setError("");
    } catch { setError("Could not save approved artwork. Check browser storage."); }
  }
  return <section aria-label="Monster artwork" className="artwork-panel">
    <h3>Monster artwork</h3>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-start" }}>
      <div style={{ width: 160, flex: "0 0 160px" }}>
        <button
          type="button"
          aria-label={showPrompt ? "Hide artwork workflow for " + monster.name : "Open artwork workflow for " + monster.name}
          aria-expanded={showPrompt}
          onClick={() => setShowPrompt(v => !v)}
          title={showPrompt ? "Hide artwork workflow" : "Click to add or change artwork"}
          style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 160, aspectRatio: "1 / 2", border: "1px solid #9ca3af", borderRadius: 8, background: "transparent", color: "inherit", cursor: "pointer", padding: 12, overflow: "hidden" }}
        >
          {approved || publishedUrl
            ? <img src={approved?.dataUrl ?? publishedUrl} alt={monster.name + " artwork"} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
            : <span style={{ textAlign: "center", color: "#6b7280" }}>click to add image...</span>}
        </button>
        {approved && <p className="muted" style={{ fontSize: "0.8rem" }}>Approved local artwork · {new Date(approved.approvedAt).toLocaleDateString()}</p>}
      </div>
      {showPrompt && <div style={{ flex: "1 1 340px", minWidth: 0, border: "1px solid #64748b", borderRadius: 8, padding: 16 }}>
        <div className="artwork-tabs" role="tablist" aria-label="Artwork source">
          <button className="artwork-tab" type="button" role="tab" aria-selected={mode === "upload"} onClick={() => setMode("upload")}>Upload</button>
          <button className="artwork-tab" type="button" role="tab" aria-selected={mode === "ai"} onClick={() => setMode("ai")}>AI Generate</button>
        </div>
        {mode === "upload" ? <div role="tabpanel">
          <p className="muted">Choose a PNG, JPEG, or WebP image (up to 8 MB) to preview before approval.</p>
          <label className="upload">Choose candidate image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => { void previewFile(e.target.files?.[0]); e.target.value = ""; }} /></label>
        </div> : <div role="tabpanel">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <label htmlFor="prepared-artwork-prompt" style={{ margin: 0 }}>Prepared image prompt</label>
            <button type="button" aria-label="Restore default prompt" title="Restore default prompt" onClick={() => setPrompt(monsterPrompt(monster, ""))} style={{ padding: 5, display: "inline-flex", alignItems: "center" }}>
              <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v6h6"/></svg>
            </button>
            <button type="button" aria-label="Clear prompt" title="Clear prompt" onClick={() => setPrompt("")} disabled={!prompt} style={{ padding: 5, display: "inline-flex", alignItems: "center" }}>
              <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m20 20-8-8"/><path d="M4 20h16"/><path d="m4 14 9-9a2 2 0 0 1 3 0l3 3a2 2 0 0 1 0 3l-9 9H7z"/></svg>
            </button>
          </div>
          <textarea id="prepared-artwork-prompt" aria-label="Prepared image prompt" style={{ display: "block", width: "100%", minHeight: 150 }} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Enter an image-generation prompt" />
          <div className="actions"><button type="button" disabled={!prompt.trim()} onClick={() => void navigator.clipboard.writeText(prompt).then(() => setNotice("Prompt copied.")).catch(() => setError("Clipboard unavailable."))}>Copy prompt</button></div>
          {!unlockedToken && <label>Encryption password to unlock API token<input type="password" autoComplete="off" value={unlockPassword} onChange={e => setUnlockPassword(e.target.value)} placeholder="Enter encryption password for this session" /></label>}
          <div className="actions"><button type="button" disabled={generating || !prompt.trim() || (!unlockedToken && !unlockPassword)} onClick={() => void generate()}>{generating ? "Generating image…" : "Generate AI artwork (paid API request)"}</button>{unlockedToken && <button type="button" onClick={() => { setUnlockedToken(null); setUnlockPassword(""); setNotice("API token locked."); }}>Lock API token</button>}</div>
        </div>}
        {candidate && <div style={{ marginTop: 16 }}>
          <p>Candidate preview</p>
          <img src={candidate} alt="Candidate artwork awaiting approval" style={{ maxWidth: "100%", maxHeight: 240, objectFit: "contain" }} />

        </div>}
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p role="status">{notice}</p>}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 20, paddingTop: 12, borderTop: "1px solid #64748b" }}>
          <button type="button" onClick={() => { setCandidate(null); setError(""); setNotice(""); setShowPrompt(false); }}>Cancel</button>
          <button type="button" disabled={!candidate} onClick={() => void approve()}>Save</button>
        </div>
      </div>}
    </div>
  </section>;
}
