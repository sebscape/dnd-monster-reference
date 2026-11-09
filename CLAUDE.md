# CLAUDE.md — dnd-monster-reference

Context for AI assistants and new contributors. Keep this current when architecture or conventions change.

## What this is

A browser-based, searchable Monster Manual for Dungeon Masters. It ships a read-only catalog of the 330 monsters from the D&D **SRD 5.2.1** (CC BY 4.0) and lets the DM create private custom (homebrew) monsters and attach artwork to any monster.

## Stack

- React 18 + TypeScript, built with Vite (`npm run dev`, `npm run build`, `npm run preview`)
- No backend database. All user data lives in the browser.
- One serverless function on Netlify (`netlify/functions/generate-artwork.mjs`) for AI image generation. In dev, `vite.config.ts` serves the same handler locally at `/.netlify/functions/generate-artwork`.
- Python scripts in `scripts/` (PyMuPDF) for the one-time SRD import pipeline.

## Layout

| Path | Purpose |
|---|---|
| `src/App.tsx` | Main app: catalog loading, search and filters, monster detail, custom monster editor, import/export |
| `src/models/monster.ts` | `Monster` type, `SCHEMA_VERSION` (1.2.0), `newMonster()`, `isMonster()` validator |
| `src/MonsterArtwork.tsx` | Per-monster artwork panel: upload, AI generation, approve/save, prompt building |
| `src/ArtworkConfiguration.tsx` | App Configuration screen (gear icon): AI provider/model, common prompt, encrypted API token, style references, custom monster import/export |
| `src/artworkSettings.ts` | Settings persistence and AES-GCM token encryption helpers |
| `public/data/published-monsters.json` | The published SRD catalog (schema 1.2.0, catalog `SRD-5.2.1-330`) |
| `public/data/monster-artwork.json` | Manifest of published artwork (currently empty) |
| `scripts/` | SRD extraction, audit, and publication pipeline (see `scripts/README.md`) |

## Data model and storage

- **Published monsters** are read-only and have `source.type = "official_srd"`. Users get an editable copy via "Create editable copy", which sets `derived_from.monster_id`.
- **Custom monsters** have `source.type = "homebrew"` and are stored in `localStorage` under `dnd-monster-reference-custom-v1`. Users back them up with JSON export/import. Import rejects non-homebrew records and duplicate UUIDs.
- Every monster has a UUID `id`; `isMonster()` enforces the UUID format.
- **Approved artwork** is stored per monster in IndexedDB (`dnd-monster-reference-approved-artwork-v1`). Style reference images are in IndexedDB (`dnd-monster-reference-artwork-v1`, store `style-references`, up to 4 used).
- **Artwork settings** are in `localStorage` under `dnd-monster-reference-artwork-settings-v1`.
- `?catalog=preview` loads `public/data/published-monsters-preview.json` instead of the real catalog (that file is gitignored).

## Importing custom monsters

`src/models/customImport.ts` (logic) and `src/CustomImportDialog.tsx` (UI). Choosing a file on the configuration screen opens a preview: **Add** (default) or **Replace** the custom library. Add finds duplicates — same UUID, or same name (case-insensitive) — and lets the user pick per monster: keep original, overwrite with new (keeps the original's UUID so artwork and battle-tracker encounters still match), or keep both (new UUID, name numbered "Name (2)"). Files with invalid records, repeated UUIDs or published UUIDs are rejected whole. **Delete all custom monsters** (small button) asks for confirmation and offers an export first.

## Security rules

- The image API token is encrypted in the browser (PBKDF2-SHA-256, 310,000 iterations → AES-256-GCM) and only decrypted when the user enters their password to generate.
- The Netlify function receives the token per request and must never store, log, or return it.
- Never commit `.env*`, `custom-monsters.json`, `private-artwork/`, or `staging/`.

## Storage bridge for companion apps

`public/bridge.html` lets [dnd-battle-tracker](https://github.com/sebscape/dnd-battle-tracker) read custom monsters and approved artwork through a hidden iframe and `postMessage`. Protocol details are in that repo's DESIGN.md.

- It is **read-only** and only answers origins on its `ALLOWED_ORIGINS` list.
- It reads the same storage keys as the app (`dnd-monster-reference-custom-v1`, IndexedDB `dnd-monster-reference-approved-artwork-v1` / `images`). **If you rename or restructure these, update `bridge.html` too**, or the battle tracker silently loses custom data.
- Don't add headers that block framing (`X-Frame-Options`, a restrictive `frame-ancestors`) for this page.

## SRD import pipeline rules

- Source of truth is the official SRD 5.2.1 PDF. **Do not substitute SRD 5.1 statistics.**
- Staging output goes to `staging/` (gitignored). Only `scripts/publish_approved_srd_catalog.py` writes to `public/data/published-monsters.json`, and the result must be reviewed in `git diff` before committing.
- Keep the CC BY 4.0 attribution and the `modifications` note in the catalog's `source` block accurate.
- **Environment tags** are the one exception to "only the publish script writes the catalog": `data/environment-tags.csv` (one row per monster: name, type, CR, environments separated by "; ", id) is the reviewed source, and `scripts/apply_environment_tags.py` copies it into each monster's `tags` (use `--check` first). The SRD has no habitat data; these were written for this project. Environments: Arctic, Coastal, Desert, Forest, Grassland, Hill, Mountain, Swamp, Underdark, Underwater, Urban, Planar. The battle tracker's encounter generator reads them, and custom monsters can use the same names as tags.
- Known provisional interpretation: Young White Dragon's Intelligence save is printed as an unsigned "2" (PDF page 340) and is recorded as +2.

## Artwork prompts

`monsterVisualDescription()` in `src/MonsterArtwork.tsx` uses a curated description when one exists in `VISUAL_DESCRIPTIONS` (currently only Aboleth), otherwise a generic template. Prompts should describe appearance only — no game mechanics, stats, or text in the image.

## Deployment

- **Live** at https://dnd-monster-ref.c2ma.com, hosted on the owner's Netlify account (project `dnd-monster-reference`) and auto-deployed from `main` on GitHub. Pushing to `main` deploys to production.
- The app is deployed independently of the C2MA homepage and should stay that way.
- The artwork function needs no Netlify environment variables: the user's API token is sent per request from the browser.
- Netlify settings live in the dashboard (no `netlify.toml`): build `npm run build`, publish `dist`, functions `netlify/functions`.
- Local dev: `npm install`, `npm run dev` (http://localhost:5173). Run `npm run build` before pushing to confirm the production build.

## Key decisions (keep unless there's a concrete reason to change)

- **SRD 5.2.1 only** for published data: a standard baseline with a clean license, instead of proprietary Monster Manual content.
- **Published and custom monsters stay separate.** Published records are read-only; custom ones are homebrew with JSON import/export.
- **Browser-local storage** (localStorage + IndexedDB) for now, to avoid the cost and complexity of accounts, a database and central image storage.
- **Explicit artwork approval.** The editor has Upload and AI Generate tabs; a candidate image only replaces the approved one when the user clicks Save. Cancel discards it.
- **Artwork frame** is vertical 1:2, 160 × 320 px. Empty frame: clicking it opens the editor. Populated frame: the image isn't clickable; a pencil icon (top right) opens the editor and a download icon (bottom right) saves the image under the monster's name.
- **Detail layout:** artwork on the left; visual description and core stats on the right. Opening the artwork editor replaces that right-hand summary.
- **AI prompts are editable,** with restore, clear and copy. The same visual description appears in the detail summary and the prompt.
- The generate button reads **"Generate With API $"** so the user knows the request costs money.
- **Encrypted token:** the user unlocks the API token once per session with a password rather than pasting a plaintext key each time.
- Dark UI with compact stat cards; the logo is meant to match the playful C2MA brand.

## Known issues and priorities (as of 2026-11-05)

1. **HTTPS certificate (verify).** The site is live, but Netlify earlier reported a Let's Encrypt provisioning failure for `dnd-monster-ref.c2ma.com`. Confirm the certificate is active in Netlify → Domain management.
2. **Git workflow (high).** Edits have been made both on the Mac and directly on GitHub, causing divergence and many merge commits. Pull before starting work; never force-push over other commits.
3. **Hosted AI generation (medium).** Verify the Netlify Function and the encrypted-token flow on the live site.
4. **Build verification (medium).** Some commits were made on GitHub without a local production build.
5. **Browser-only data (high, by design for now).** Custom monsters and artwork don't sync between browsers, devices or users. IndexedDB quotas and backups need thought.
6. **Accessibility and mobile (medium).** Test the compact artwork controls, keyboard navigation and editor layout at different screen sizes.
7. **Future: multi-user hosting.** Making this a hosted service on the C2MA site would need accounts, central storage, permissions and possibly billing. Decide between "browser-local utility" and "synced multi-user app" before adding accounts.

Recommended order: confirm HTTPS → stabilize git and confirm the build → end-to-end test (search, custom monster CRUD, import/export, artwork upload/generate/approve/cancel/download, persistence after refresh) → decide on data portability → release prep (attribution, accessibility, error handling, API usage limits, backups, monitoring).

## Other gaps

- No automated tests.
- The top-level README is a single line.
- Many scripts in `scripts/` were one-off audits during import (pilot monsters, Young White Dragon review) and are not needed for day-to-day work.
