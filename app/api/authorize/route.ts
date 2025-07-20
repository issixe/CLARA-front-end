import { NextResponse } from "next/server";

// TODO: Replace with actual scopes list import when available
// Expected to be an array of Google Fit OAuth scope strings
import { FIT_SCOPES } from "@/lib/constants";

  // 1. Generate a unique `state` parameter to prevent CSRF
  const state = crypto.randomUUID();

  // 2. Persist `state` in an HTTP-only, encrypted cookie
cookies().set(
    "oauth_state",
    state,
    {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
    }
  );

  // 3. Build Google OAuth consent URL
  const scope = `openid email profile ${FIT_SCOPES.join(" ")}`;

  const params = new URLSearchParams({
    client_id: process.env.GOOGLE_CLIENT_ID as string,
    redirect_uri: process.env.GOOGLE_REDIRECT_URI as string, // e.g. http://127.0.0.1/oauth2callback
    response_type: "code",
    scope,
    access_type: "offline",
    include_granted_scopes: "true",
    prompt: "consent",
    state,
  });

  const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;

  // 4. Redirect the user to Google for consent
  return NextResponse.redirect(authUrl);

