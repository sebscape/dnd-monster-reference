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
  const [extra, setExtra] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);
  const [unlockPassword, setUnlockPassword] = useState("");
  const [unlockedToken, setUnlockedToken] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    setApproved(undefined); setCandidate(null); setExtra(""); setError(""); setNotice(""); setShowPrompt(false);
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
      setApproved(record); setCandidate(null); setNotice("Artwork approved and saved privately in this browser."); setError("");
    } catch { setError("Could not save approved artwork. Check browser storage."); }
  }
  const prompt = monsterPrompt(monster, extra);
  return <section aria-label="Monster artwork" className="artwork-panel">
    <h3>Monster artwork</h3>
    <button
      type="button"
      aria-label={showPrompt ? "Hide artwork workflow for " + monster.name : "Open artwork workflow for " + monster.name}
      aria-expanded={showPrompt}
      onClick={() => setShowPrompt(v => !v)}
      title={showPrompt ? "Hide artwork workflow" : "Click to add or change artwork"}
      style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "100%", maxWidth: 160, aspectRatio: "1 / 2", border: "1px solid #9ca3af", borderRadius: 8, background: "transparent", color: "inherit", cursor: "pointer", padding: 12, overflow: "hidden" }}
    >
      {approved || publishedUrl
        ? <img src={approved?.dataUrl ?? publishedUrl} alt={monster.name + " artwork"} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
        : <span style={{ textAlign: "center", color: "#6b7280" }}>click to add image...</span>}
    </button>
    {approved && <p className="muted">Approved local artwork · {new Date(approved.approvedAt).toLocaleDateString()}</p>}
    {showPrompt && <div style={{ marginTop: 12 }}>
      <p className="muted">Step 1: Review the prompt. Generation uses your OpenAI API account and may incur charges.</p>
      <label>Additional instructions<textarea style={{ display: "block", width: "100%", minHeight: 70 }} value={extra} onChange={e => setExtra(e.target.value)} placeholder="Optional monster-specific art direction" /></label>
      <label>Prepared image prompt<textarea style={{ display: "block", width: "100%", minHeight: 180 }} value={prompt} readOnly /></label>
      <div className="actions"><button type="button" onClick={() => void navigator.clipboard.writeText(prompt).then(() => setNotice("Prompt copied.")).catch(() => setError("Clipboard unavailable."))}>Copy prompt</button></div>
      {!unlockedToken && <label>Encryption password to unlock API token<input type="password" autoComplete="off" value={unlockPassword} onChange={e => setUnlockPassword(e.target.value)} placeholder="Enter encryption password for this session" /></label>}
      <div className="actions"><button type="button" disabled={generating || (!unlockedToken && !unlockPassword)} onClick={() => void generate()}>{generating ? "Generating image…" : "Generate AI artwork (paid API request)"}</button>{unlockedToken && <button type="button" onClick={() => { setUnlockedToken(null); setUnlockPassword(""); setNotice("API token locked."); }}>Lock API token</button>}</div>
      <p className="muted">Step 2: Preview the AI result or import an image manually. Approve only when satisfied. Approved images are saved locally by monster UUID. Artwork generation is available through the configured local development handler or deployed function.</p>
      <label className="upload">Choose candidate image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => { void previewFile(e.target.files?.[0]); e.target.value = ""; }} /></label>
      {candidate && <div style={{ marginTop: 12 }}><img src={candidate} alt="Candidate artwork awaiting approval" style={{ maxWidth: "100%", maxHeight: 320, objectFit: "contain" }} /><div className="actions"><button type="button" onClick={() => void approve()}>Approve artwork</button><button type="button" onClick={() => { const link = document.createElement("a"); link.href = candidate; link.download = monster.name.toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-candidate.png"; link.click(); }}>Download candidate</button><button type="button" onClick={() => { setCandidate(null); setNotice("Candidate discarded."); }}>Discard candidate</button></div></div>}
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
    </div>}
  </section>;
}
