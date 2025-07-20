import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { FIT_SCOPES } from "@/lib/constants";

export async function GET() {
  // Generate anti-CSRF state
  const state = crypto.randomUUID();

  // Build the redirect response first so we can attach cookies safely

  // Build Google OAuth URL
  const scope = `openid email profile ${FIT_SCOPES.join(" ")}`;
  const params = new URLSearchParams({
    client_id: process.env.GOOGLE_CLIENT_ID as string,
    redirect_uri: process.env.GOOGLE_REDIRECT_URI as string,
    response_type: "code",
    scope,
    access_type: "offline",
    include_granted_scopes: "true",
    prompt: "consent",
    state,
  });

  const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;

  const resp = NextResponse.redirect(authUrl);
  resp.cookies.set("oauth_state", state, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });
  return resp;
}

