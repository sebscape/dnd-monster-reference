import { defineConfig, type Plugin } from "vite";
import handler from "./netlify/functions/generate-artwork.mjs";

function localArtworkApi(): Plugin {
  return {
    name: "local-artwork-api",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use("/.netlify/functions/generate-artwork", async (req, res) => {
        res.setHeader("Cache-Control", "no-store");
        res.setHeader("Content-Type", "application/json");
        if (req.method !== "POST") {
          res.statusCode = 405;
          res.end(JSON.stringify({ error: "POST required." }));
          return;
        }
        try {
          const chunks: Buffer[] = [];
          let size = 0;
          for await (const chunk of req) {
            const data = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
            size += data.length;
            if (size > 30 * 1024 * 1024) {
              res.statusCode = 413;
              res.end(JSON.stringify({ error: "Artwork request exceeds the 30 MB limit." }));
              return;
            }
            chunks.push(data);
          }
          const request = new Request("http://localhost/.netlify/functions/generate-artwork", {
            method: "POST",
            headers: { "content-type": req.headers["content-type"] || "application/json" },
            body: Buffer.concat(chunks),
          });
          const result = await handler(request);
          res.statusCode = result.status;
          res.end(Buffer.from(await result.arrayBuffer()));
        } catch (error) {
          server.config.logger.error("Local artwork generation request failed.");
          res.statusCode = 500;
          res.end(JSON.stringify({ error: error instanceof Error ? error.message : "Generation request failed." }));
        }
      });
    },
  };
}

export default defineConfig({ base: "/", plugins: [localArtworkApi()] });
