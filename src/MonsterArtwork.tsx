import { useEffect, useState } from "react";
import type { Monster } from "./models/monster";
import { loadSettings } from "./artworkSettings";

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
export function monsterPrompt(monster: Monster, extra: string): string {
  const settings = loadSettings();
  const details = [
    monster.name + " — " + monster.size + " " + monster.type,
    monster.alignment ? "Alignment: " + monster.alignment : "",
    monster.traits?.slice(0, 4).map(t => t.name + ": " + t.description).join("\n") ?? "",
    extra.trim()
  ].filter(Boolean);
  return [settings.commonPrompt, ...details].join("\n\n");
}
export default function MonsterArtwork({ monster, publishedUrl }: { monster: Monster; publishedUrl?: string }) {
  const [approved, setApproved] = useState<Stored>();
  const [candidate, setCandidate] = useState<string | null>(null);
  const [extra, setExtra] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);
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
    {approved ? <><img src={approved.dataUrl} alt={monster.name + " approved illustration"} style={{ maxWidth: "100%", maxHeight: 320, objectFit: "contain" }} /><p className="muted">Approved local artwork · {new Date(approved.approvedAt).toLocaleDateString()}</p></> :
      publishedUrl ? <img src={publishedUrl} alt={monster.name + " published illustration"} style={{ maxWidth: "100%", maxHeight: 320, objectFit: "contain" }} /> :
      <p className="muted">No artwork approved yet.</p>}
    <div className="actions"><button type="button" onClick={() => setShowPrompt(v => !v)}>{showPrompt ? "Hide artwork workflow" : "Generate / import artwork"}</button></div>
    {showPrompt && <div style={{ marginTop: 12 }}>
      <p className="muted">Step 1: Review the prompt assembled from App Configuration and this monster. AI API generation will be connected in the next phase; this screen does not send paid requests.</p>
      <label>Additional instructions<textarea style={{ display: "block", width: "100%", minHeight: 70 }} value={extra} onChange={e => setExtra(e.target.value)} placeholder="Optional monster-specific art direction" /></label>
      <label>Prepared image prompt<textarea style={{ display: "block", width: "100%", minHeight: 180 }} value={prompt} readOnly /></label>
      <div className="actions"><button type="button" onClick={() => void navigator.clipboard.writeText(prompt).then(() => setNotice("Prompt copied.")).catch(() => setError("Clipboard unavailable."))}>Copy prompt</button></div>
      <p className="muted">Step 2: Import an image to preview it before approving. Approved images are associated with the monster UUID and stored in this browser.</p>
      <label className="upload">Choose candidate image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => { void previewFile(e.target.files?.[0]); e.target.value = ""; }} /></label>
      {candidate && <div style={{ marginTop: 12 }}><img src={candidate} alt="Candidate artwork awaiting approval" style={{ maxWidth: "100%", maxHeight: 320, objectFit: "contain" }} /><div className="actions"><button type="button" onClick={() => void approve()}>Approve artwork</button><button type="button" onClick={() => { setCandidate(null); setNotice("Candidate discarded."); }}>Discard candidate</button></div></div>}
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
    </div>}
  </section>;
}
