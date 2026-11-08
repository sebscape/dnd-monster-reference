import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
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
export function monsterVisualDescription(monster: Monster): string {
  const curated = VISUAL_DESCRIPTIONS[monster.name.trim().toLowerCase()];
  return curated ?? [
    "Depict a recognizable " + monster.name + ", a " + monster.size.toLowerCase() + " " + monster.type.toLowerCase() + " fantasy creature.",
    "Use distinctive physical features associated with this creature, emphasizing silhouette, anatomy, textures, and a clear miniature-friendly pose.",
    "Do not depict game rules, statistics, text, symbols, or magical effects unless they are essential to the creature's visible appearance."
  ].join(" ");
}
export function monsterPrompt(monster: Monster, extra: string): string {
  const settings = loadSettings();
  const visualDescription = monsterVisualDescription(monster);
  return [
    settings.commonPrompt,
    "Creature: " + monster.name,
    "Visual description: " + visualDescription,
    "Composition: Show the entire creature, including all limbs, fins, tail, and tentacles, inside a vertical 1:2 portrait frame. Keep a true transparent background, with no scenery, lettering, border, or cropped extremities.",
    extra.trim()
  ].filter(Boolean).join("\n\n");
}
export default function MonsterArtwork({ monster, publishedUrl, summary }: { monster: Monster; publishedUrl?: string; summary: ReactNode }) {
  const [approved, setApproved] = useState<Stored>();
  const [candidate, setCandidate] = useState<string | null>(null);
  const [prompt, setPrompt] = useState(() => monsterPrompt(monster, ""));
  const [showPrompt, setShowPrompt] = useState(false);
  const [mode, setMode] = useState<"upload" | "ai">("upload");
  const [unlockPassword, setUnlockPassword] = useState("");
  const [unlockedToken, setUnlockedToken] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const activeJob = useRef<{ id: string; secret: string; canceled: boolean } | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    setApproved(undefined); setCandidate(null); setPrompt(monsterPrompt(monster, "")); setError(""); setNotice(""); setShowPrompt(false); setMode("upload");
    void readImage(monster.id).then(v => { if (active) setApproved(v); }).catch(() => { if (active) setError("Could not load local approved artwork."); });
    return () => { active = false; const job = activeJob.current; if (job) { job.canceled = true; void cancelRemoteJob(job); activeJob.current = null; } };
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
  async function cancelRemoteJob(job: { id: string; secret: string }) {
    try {
      await fetch("/.netlify/functions/artwork-job?id=" + encodeURIComponent(job.id), {
        method: "DELETE", headers: { "X-Artwork-Job-Secret": job.secret }
      });
    } catch { /* Cancellation is best-effort; ignored results cannot replace artwork. */ }
  }
  function cancelGeneration() {
    const job = activeJob.current;
    if (job) { job.canceled = true; activeJob.current = null; void cancelRemoteJob(job); }
    setGenerating(false);
    setNotice("Generation canceled. API charges may still apply if processing started.");
    setError("");
  }
  async function generate() {
    if (generating || activeJob.current) return;
    if (!prompt.trim()) { setError("Enter an image prompt before generating."); return; }
    setError(""); setNotice("");
    const settings = loadSettings();
    if (settings.provider !== "OpenAI") { setError("Select OpenAI in App Configuration."); return; }
    if (!settings.encryptedToken) { setError("Configure an encrypted API token first."); return; }
    const job = { id: crypto.randomUUID(), secret: crypto.randomUUID(), canceled: false };
    activeJob.current = job;
    setGenerating(true);
    try {
      const token = unlockedToken ?? await decryptToken(settings.encryptedToken, unlockPassword);
      if (job.canceled) return;
      if (!unlockedToken) { setUnlockedToken(token); setUnlockPassword(""); }
      const refs = await loadReferences();
      if (job.canceled) return;
      const payload = { id: job.id, secret: job.secret, token, model: settings.model.trim() || "gpt-image-1.5", prompt, references: refs };
      // The Vite development server uses the existing synchronous handler.
      // Netlify production uses background functions to avoid gateway timeouts.
      if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
        const response = await fetch("/.netlify/functions/generate-artwork", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
        });
        const result: { image?: string; error?: string } = await response.json();
        if (job.canceled) return;
        if (!response.ok || !result.image?.startsWith("data:image/png;base64,")) throw new Error(result.error || "Image generation failed.");
        setCandidate(result.image);
      } else {
        const statusUrl = "/.netlify/functions/artwork-job?id=" + encodeURIComponent(job.id);
        const headers = { "X-Artwork-Job-Secret": job.secret };
        const created = await fetch(statusUrl, { method: "POST", headers });
        if (!created.ok) throw new Error("Could not create artwork job.");
        if (job.canceled) { void cancelRemoteJob(job); return; }
        const started = await fetch("/.netlify/functions/generate-artwork-background", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
        });
        if (!started.ok) throw new Error("Could not start background generation (HTTP " + started.status + ").");
        const deadline = Date.now() + 14 * 60 * 1000;
        while (!job.canceled && Date.now() < deadline) {
          await new Promise(resolve => setTimeout(resolve, 2500));
          if (job.canceled) return;
          const response = await fetch(statusUrl, { headers });
          if (!response.ok) throw new Error("Unable to check artwork generation status.");
          const result: { state: string; image?: string; error?: string } = await response.json();
          if (job.canceled) return;
          if (result.state === "done") {
            if (!result.image?.startsWith("data:image/png;base64,")) throw new Error("Generated image is missing.");
            setCandidate(result.image);
            break;
          }
          if (result.state === "error") throw new Error(result.error || "Image generation failed.");
          if (result.state === "canceled") return;
        }
        if (Date.now() >= deadline && !job.canceled) throw new Error("Generation exceeded the waiting limit.");
      }
      if (!job.canceled) setNotice("AI image generated. Review it before approving; each generation may incur an API charge.");
    } catch (e) {
      if (!job.canceled) {
        if (e instanceof DOMException && e.name === "OperationError") setError("Incorrect encryption password. Try again.");
        else setError(e instanceof Error ? e.message : "Image generation failed.");
      }
    } finally {
      if (activeJob.current === job) { activeJob.current = null; setGenerating(false); }
    }
  }
  async function approve() {
    if (!candidate) return;
    try {
      const record = { monsterId: monster.id, dataUrl: candidate, approvedAt: new Date().toISOString() };
      await saveImage(record);
      setApproved(record); setCandidate(null); setShowPrompt(false); setNotice(""); setError("");
    } catch { setError("Could not save approved artwork. Check browser storage."); }
  }
  async function downloadArtwork() {
    const imageUrl = approved?.dataUrl ?? publishedUrl;
    if (!imageUrl) return;
    try {
      const response = await fetch(imageUrl);
      if (!response.ok) throw new Error("Image download failed.");
      const blob = await response.blob();
      const extension = blob.type === "image/jpeg" ? "jpg" : blob.type === "image/webp" ? "webp" : "png";
      const filename = (monster.name.trim().replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "monster") + "." + extension;
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch {
      setError("Unable to download this artwork. Try opening the image in a new tab.");
      setShowPrompt(true);
    }
  }
  return <section aria-label="Monster artwork" className="artwork-panel">
    <h3>Monster artwork</h3>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-start" }}>
      <div style={{ width: 160, flex: "0 0 160px" }}>
        {approved || publishedUrl ? <div style={{ position: "relative", width: 160, aspectRatio: "1 / 2", border: "1px solid #9ca3af", borderRadius: 8, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", padding: 12 }}>
          <img src={approved?.dataUrl ?? publishedUrl} alt={monster.name + " artwork"} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
          <button type="button" aria-label={"Edit artwork for " + monster.name} title="Edit artwork" aria-expanded={showPrompt} onClick={() => setShowPrompt(true)} style={{ position: "absolute", top: 6, right: 6, width: 32, height: 32, padding: 6, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "50%", background: "#34465d", border: "1px solid #9ca3af", color: "#fff" }}>
            <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L9 17l-4 1 1-4z"/></svg>
          </button>
          <button type="button" aria-label={"Download artwork for " + monster.name} title="Download artwork" onClick={() => void downloadArtwork()} style={{ position: "absolute", bottom: 6, right: 6, width: 32, height: 32, padding: 6, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "50%", background: "#34465d", border: "1px solid #9ca3af", color: "#fff" }}>
            <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 17v4h14v-4"/></svg>
          </button>
        </div> : <button
          type="button"
          aria-label={"Open artwork workflow for " + monster.name}
          aria-expanded={showPrompt}
          onClick={() => setShowPrompt(v => !v)}
          title="Click to add artwork"
          style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 160, aspectRatio: "1 / 2", border: "1px solid #9ca3af", borderRadius: 8, background: "transparent", color: "inherit", cursor: "pointer", padding: 12, overflow: "hidden" }}
        ><span style={{ textAlign: "center", color: "#6b7280" }}>click to add image...</span></button>}
        {approved && <p className="muted" style={{ fontSize: "0.8rem" }}>Approved local artwork · {new Date(approved.approvedAt).toLocaleDateString()}</p>}
      </div>
      {!showPrompt ? <div className="artwork-summary" style={{ flex: "1 1 340px", minWidth: 0 }}>{summary}</div> : <div style={{ flex: "1 1 340px", minWidth: 0, border: "1px solid #64748b", borderRadius: 8, padding: 16 }}>
        <div className="artwork-tabs" role="tablist" aria-label="Artwork source">
          <button className="artwork-tab" type="button" role="tab" aria-selected={mode === "upload"} onClick={() => { if (generating) cancelGeneration(); setMode("upload"); }}>Upload</button>
          <button className="artwork-tab" type="button" role="tab" aria-selected={mode === "ai"} onClick={() => setMode("ai")}>AI Generate</button>
        </div>
        {mode === "upload" ? <div role="tabpanel">
          <p className="muted">Choose a PNG, JPEG, or WebP image (up to 8 MB) to preview before approval.</p>
          <label className="upload">Choose Image ...<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => { void previewFile(e.target.files?.[0]); e.target.value = ""; }} /></label>
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
          <div className="actions" style={{ marginTop: 12, marginBottom: 16 }}><button type="button" disabled={!prompt.trim()} onClick={() => void navigator.clipboard.writeText(prompt).then(() => setNotice("Prompt copied.")).catch(() => setError("Clipboard unavailable."))}>Copy prompt</button></div>
          <div style={{ display: "flex", alignItems: "flex-end", flexWrap: "wrap", gap: 12 }}>
            <button type="button" disabled={generating || !prompt.trim() || (!unlockedToken && !unlockPassword)} onClick={() => void generate()}>{generating ? "Generating image…" : "Generate With API $"}</button>
            {!unlockedToken ? <label style={{ flex: "1 1 200px", minWidth: 0, margin: 0 }}>Encryption password to unlock API token<input type="password" autoComplete="off" value={unlockPassword} onChange={e => setUnlockPassword(e.target.value)} placeholder="Encryption password" style={{ width: "100%" }} /></label>
            : <button type="button" onClick={() => { setUnlockedToken(null); setUnlockPassword(""); setNotice("API token locked."); }}>Lock API token</button>}
          </div>
        </div>}
        {(generating || candidate) && <div style={{ marginTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", width: "100%", minHeight: 240 }}>
            {generating
              ? <img src="/images/iridescent-spinner.gif" alt="Generating artwork, please wait" role="status" style={{ display: "block", height: 240, maxWidth: "100%", objectFit: "contain" }} />
              : <img src={candidate ?? undefined} alt="Candidate artwork awaiting approval" style={{ display: "block", maxWidth: "100%", maxHeight: 240, objectFit: "contain" }} />}
          </div>
        </div>}
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p role="status">{notice}</p>}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 20, paddingTop: 12, borderTop: "1px solid #64748b" }}>
          <button type="button" onClick={() => { if (generating) cancelGeneration(); setCandidate(null); setError(""); setNotice(""); setShowPrompt(false); }}>{generating ? "Cancel Generation" : "Cancel"}</button>
          <button type="button" disabled={generating || !candidate} onClick={() => void approve()}>Save</button>
        </div>
      </div>}
    </div>
  </section>;
}
