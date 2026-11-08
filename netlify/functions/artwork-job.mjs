import { getStore } from "@netlify/blobs";

const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" }
});
const validId = id => typeof id === "string" && /^[a-f0-9-]{36}$/.test(id);
const validSecret = secret => typeof secret === "string" && /^[a-f0-9-]{36}$/.test(secret);
const key = id => "job-" + id;

export default async function handler(request) {
  try {
    const url = new URL(request.url);
    const id = url.searchParams.get("id");
    const secret = request.headers.get("X-Artwork-Job-Secret");
    if (!validId(id) || !validSecret(secret)) return json({ error: "Invalid job credentials." }, 400);
    const store = getStore("artwork-generation-jobs");
    const job = await store.get(key(id), { type: "json" });
    if (request.method === "POST") {
      if (job) return json({ error: "Job already exists." }, 409);
      await store.setJSON(key(id), { secret, state: "pending", created: Date.now() });
      return json({ state: "pending" }, 201);
    }
    if (!job || job.secret !== secret) return json({ error: "Job not found." }, 404);
    if (request.method === "DELETE") {
      await store.setJSON(key(id), { secret, state: "canceled", created: job.created });
      return json({ state: "canceled" });
    }
    if (request.method !== "GET") return json({ error: "Method not allowed." }, 405);
    if (Date.now() - job.created > 15 * 60 * 1000 && job.state === "pending") {
      return json({ state: "error", error: "Generation exceeded the 15-minute limit." });
    }
    return json(job.state === "done" ? { state: "done", image: job.image } :
      job.state === "error" ? { state: "error", error: job.error } : { state: job.state });
  } catch (error) {
    return json({ error: error instanceof Error ? error.message : "Job status unavailable." }, 500);
  }
}
