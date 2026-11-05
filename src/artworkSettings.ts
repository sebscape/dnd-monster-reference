export const SETTINGS_KEY = "dnd-monster-reference-artwork-settings-v1";
export type EncryptedToken = { algorithm: "AES-256-GCM"; kdf: "PBKDF2-SHA-256"; iterations: number; salt: string; iv: string; ciphertext: string };
export type Settings = { provider: string; model: string; commonPrompt: string; version: number; encryptedToken?: EncryptedToken };
const DEFAULT_PROMPT = "Create an original fantasy bestiary illustration of the specified creature. Show the entire creature with a clear silhouette, consistent lighting and brushwork, and a true transparent background. No text, labels, scenery, or borders.";
export const defaults: Settings = { provider: "OpenAI", model: "", commonPrompt: DEFAULT_PROMPT, version: 1 };
const toBase64 = (bytes: Uint8Array): string => btoa(Array.from(bytes, b => String.fromCharCode(b)).join(""));
const fromBase64 = (value: string): Uint8Array => Uint8Array.from(atob(value), c => c.charCodeAt(0));
async function derive(password: string, salt: Uint8Array, iterations: number): Promise<CryptoKey> {
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt, iterations }, base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}
export async function encryptToken(token: string, password: string): Promise<EncryptedToken> {
  if (!token || !password) throw new Error("Token and encryption password are required.");
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const iterations = 310000;
  const key = await derive(password, salt, iterations);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(token));
  return { algorithm: "AES-256-GCM", kdf: "PBKDF2-SHA-256", iterations, salt: toBase64(salt), iv: toBase64(iv), ciphertext: toBase64(new Uint8Array(ciphertext)) };
}
export async function decryptToken(encrypted: EncryptedToken, password: string): Promise<string> {
  if (encrypted.algorithm !== "AES-256-GCM" || encrypted.kdf !== "PBKDF2-SHA-256" || encrypted.iterations !== 310000) throw new Error("Unsupported encryption settings.");
  const key = await derive(password, fromBase64(encrypted.salt), encrypted.iterations);
  const result = await crypto.subtle.decrypt({ name: "AES-GCM", iv: fromBase64(encrypted.iv) }, key, fromBase64(encrypted.ciphertext));
  return new TextDecoder().decode(result);
}
export function loadSettings(): Settings {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? "null");
    if (parsed && typeof parsed === "object") {
      const p = parsed as Partial<Settings>;
      if (typeof p.commonPrompt === "string" && typeof p.provider === "string")
        return { provider: p.provider, model: typeof p.model === "string" ? p.model : "", commonPrompt: p.commonPrompt, version: Number.isInteger(p.version) ? p.version! : 1, ...(p.encryptedToken && typeof p.encryptedToken.ciphertext === "string" ? { encryptedToken: p.encryptedToken } : {}) };
    }
  } catch { /* defaults */ }
  return defaults;
}
export function saveSettings(settings: Settings): void { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); }
