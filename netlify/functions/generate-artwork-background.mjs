import { getStore } from "@netlify/blobs";
import generateArtwork from "./generate-artwork.mjs";

// Netlify recognizes the -background suffix and returns 202 immediately.
// The OpenAI token is used in this invocation only; it is never persisted.
export default async function handler(request) {
  if (request.method !== "POST") return;
  let id;
  let secret;
  try {
    const payload = await request.json();
    ({ id, secret } = payload);
    if (typeof id !== "string" || !/^[a-f0-9-]{36}$/.test(id) ||
        typeof secret !== "string" || !/^[a-f0-9-]{36}$/.test(secret)) return;
    const store = getStore({ name: "artwork-generation-jobs", consistency: "strong" });
    const key = "job-" + id;
    const current = await store.get(key, { type: "json" });
    if (!current || current.secret !== secret || current.state !== "pending") return;
    try {
      const generationRequest = new Request("https://localhost/.netlify/functions/generate-artwork", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: payload.token, model: payload.model, prompt: payload.prompt, references: payload.references })
      });
      const response = await generateArtwork(generationRequest);
      const result = await response.json();
      const latest = await store.get(key, { type: "json" });
      if (!latest || latest.secret !== secret || latest.state === "canceled") return;
      if (!response.ok || !result.image) {
        await store.setJSON(key, { secret, state: "error", created: current.created, error: result.error || "Image generation failed." });
      } else {
        await store.setJSON(key, { secret, state: "done", created: current.created, image: result.image });
      }
    } catch (error) {
      const latest = await store.get(key, { type: "json" });
      if (latest && latest.secret === secret && latest.state !== "canceled") {
        await store.setJSON(key, { secret, state: "error", created: current.created, error: error instanceof Error ? error.message : "Generation failed." });
      }
    }
  } catch (error) {
    // Never log credentials or request bodies.
    console.error("Background artwork generation could not start:", error instanceof Error ? error.message : "Unknown error");
  }
}
