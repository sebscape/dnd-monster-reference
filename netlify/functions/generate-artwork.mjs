// Netlify Function: POST /.netlify/functions/generate-artwork
// The caller's API token is never stored, logged, or included in the response.
export default async function handler(request) {
  if (request.method !== "POST") return new Response(JSON.stringify({ error: "POST required" }), { status: 405, headers: { "Content-Type": "application/json" } });
  try {
    const { token, model, prompt, references } = await request.json();
    if (typeof token !== "string" || !token.startsWith("sk-") || token.length > 512)
      return new Response(JSON.stringify({ error: "A valid OpenAI API token is required." }), { status: 400 });
    const allowed = ["gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"];
    if (!allowed.includes(model)) return new Response(JSON.stringify({ error: "Unsupported image model." }), { status: 400 });
    if (typeof prompt !== "string" || !prompt.trim() || prompt.length > 32000)
      return new Response(JSON.stringify({ error: "Prompt is missing or too long." }), { status: 400 });
    if (!Array.isArray(references) || references.length > 4)
      return new Response(JSON.stringify({ error: "Up to four style references are supported." }), { status: 400 });
    const useReferences = references.length > 0;
    let endpoint;
    let options;
    if (useReferences) {
      const form = new FormData();
      form.append("model", model);
      form.append("prompt", prompt);
      form.append("background", "transparent");
      form.append("output_format", "png");
      form.append("size", "1024x1536");
      for (let i = 0; i < references.length; i++) {
        const ref = references[i];
        if (typeof ref !== "string" || !/^data:image\/(png|jpeg|webp);base64,/.test(ref) || ref.length > 7_000_000)
          return new Response(JSON.stringify({ error: "Invalid style reference." }), { status: 400 });
        const match = ref.match(/^data:(image\/(?:png|jpeg|webp));base64,(.*)$/s);
        const bytes = Uint8Array.from(atob(match[2]), c => c.charCodeAt(0));
        form.append("image[]", new Blob([bytes], { type: match[1] }), "reference-" + i + (match[1] === "image/png" ? ".png" : match[1] === "image/webp" ? ".webp" : ".jpg"));
      }
      endpoint = "https://api.openai.com/v1/images/edits";
      options = { method: "POST", headers: { Authorization: "Bearer " + token }, body: form };
    } else {
      endpoint = "https://api.openai.com/v1/images/generations";
      options = { method: "POST", headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" }, body: JSON.stringify({ model, prompt, background: "transparent", output_format: "png", size: "1024x1536", n: 1 }) };
    }
    const response = await fetch(endpoint, options);
    const result = await response.json();
    if (!response.ok) return new Response(JSON.stringify({ error: result?.error?.message || "OpenAI request failed." }), { status: response.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
    const image = result?.data?.[0]?.b64_json;
    if (typeof image !== "string" || !image) throw new Error("No image returned.");
    return new Response(JSON.stringify({ image: "data:image/png;base64," + image }), { status: 200, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch (e) {
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Generation failed." }), { status: 500, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  }
}
export const config = { path: "/.netlify/functions/generate-artwork" };
