import { cookies } from "next/headers";
import { OAuth2Client } from "google-auth-library";

/**
 * List of Google Fit OAuth scopes required by the application.
 * Extend as your app needs additional access to Google Fit data sets.
 */
export const FIT_SCOPES: string[] = [
  "https://www.googleapis.com/auth/fitness.activity.read",
  "https://www.googleapis.com/auth/fitness.location.read",
  "https://www.googleapis.com/auth/fitness.body.read",
  "https://www.googleapis.com/auth/fitness.heart_rate.read",
  "https://www.googleapis.com/auth/fitness.sleep.read",
];

/**
 * Builds and returns a Google OAuth2 client that is pre-configured with the
 * client ID, secret and redirect URI taken from environment variables.
 *
 * Environment variables expected:
 *   - GOOGLE_CLIENT_ID
 *   - GOOGLE_CLIENT_SECRET
 *   - GOOGLE_REDIRECT_URI
 */
interface ClientJSON {
  installed?: {
    client_id: string;
    client_secret: string;
    redirect_uris: string[];
  };
  web?: {
    client_id: string;
    client_secret: string;
    redirect_uris: string[];
  };
}

function readClientSecrets(): { id: string; secret: string; redirectUri: string } | null {
  try {
    const data = require("fs").readFileSync("client_secret.json", "utf8");
    const json: ClientJSON = JSON.parse(data);
    const cfg = json.installed ?? json.web;
    if (!cfg) return null;
    return {
      id: cfg.client_id,
      secret: cfg.client_secret,
      redirectUri: cfg.redirect_uris[0],
    };
  } catch {
    return null;
  }
}

export function buildOAuthClient(): OAuth2Client {
  const fileCreds = readClientSecrets();
  const clientId = fileCreds?.id ?? process.env.GOOGLE_CLIENT_ID;
  const clientSecret = fileCreds?.secret ?? process.env.GOOGLE_CLIENT_SECRET;
  const redirectUri = fileCreds?.redirectUri ?? process.env.GOOGLE_REDIRECT_URI;

  if (!clientId || !redirectUri) {
    throw new Error("Google OAuth credentials not found. Add client_secret.json or env vars.");
  }

  return new OAuth2Client({
    clientId,
    clientSecret,
    redirectUri,
  });
}

/**
 * Verifies that every required Google Fit scope has been granted.
 * @param granted Space-delimited scopes string returned by Google.
 * @returns `true` if all FIT_SCOPES are present, otherwise `false`.
 */
export function hasRequiredScopes(granted: string | null | undefined): boolean {
  if (!granted) return false;
  const grantedArray = granted.split(" ").filter(Boolean);
  return FIT_SCOPES.every((scope) => grantedArray.includes(scope));
}

// ---------------------------------------------------------------------------
// Cookie encryption helper
// ---------------------------------------------------------------------------

/**
 * Minimal subset of cookie options we care about. You can extend this as needed.
 */
export interface CookieOptions {
  httpOnly?: boolean;
  secure?: boolean;
  sameSite?: "lax" | "strict" | "none";
  path?: string;
  maxAge?: number;
  expires?: Date;
}

/**
 * Sets an encrypted, Base64-encoded cookie using the Web Crypto API (AES-GCM).
 *
 * NOTE: This helper is meant for development usage where a lightweight
 * encryption strategy suffices. For production, consider a battle-tested
 * solution such as the `iron-session` or `next-session` packages, a server-
 * side database, or an external KMS.
 */
export async function setEncryptedCookie(
  name: string,
  value: string,
  options: CookieOptions = {}
): Promise<void> {
  // Derive a symmetric key from an environment variable (or fallback in dev).
  const secret =
    process.env.COOKIE_ENCRYPTION_SECRET ??
    "dev_secret_key_32_bytes_long________"; // must be ≥ 32 chars

  const encoder = new TextEncoder();
  const keyMaterial = encoder.encode(secret).slice(0, 32); // 256-bit key
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    keyMaterial,
    { name: "AES-GCM" },
    false,
    ["encrypt"]
  );

  // AES-GCM requires a 12-byte IV.
  const iv = crypto.getRandomValues(new Uint8Array(12));

  // Encrypt the plaintext value.
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    cryptoKey,
    encoder.encode(value)
  );

  // Concatenate IV + ciphertext so we can decode later.
  const combined = new Uint8Array(iv.byteLength + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), iv.byteLength);

  const encoded = Buffer.from(combined).toString("base64");

  // Merge default cookie settings with caller-provided options.
  cookies().set(name, encoded, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    ...options,
  });
}

