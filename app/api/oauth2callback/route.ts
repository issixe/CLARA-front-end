import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { OAuth2Client, Credentials } from "google-auth-library";

import { FIT_SCOPES } from "@/lib/constants";

// The OAuth2 redirect handler for Google Fit authorization.
// This route exchanges the `code` for access/refresh tokens,
// validates the granted scopes and stores the resulting token
// response in a secure (HTTP-only) cookie while also clearing
// the original `oauth_state` CSRF cookie.
export async function GET(request: Request) {
  const url = new URL(request.url);
  const state = url.searchParams.get("state");
  const code = url.searchParams.get("code");

  // 1. Basic validation – both params must be present
  if (!state || !code) {
    return NextResponse.redirect("/unsuccessful");
  }

  // 2. Compare incoming `state` with the value stored in cookie
  const cookieStore = cookies();
  const storedState = cookieStore.get("oauth_state")?.value;

  if (!storedState || storedState !== state) {
    return NextResponse.redirect("/unsuccessful");
  }

  // 3. Exchange the auth `code` for tokens using Google OAuth2 client
  const oauth2Client = new OAuth2Client({
    clientId: process.env.GOOGLE_CLIENT_ID,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    redirectUri: process.env.GOOGLE_REDIRECT_URI, // e.g. http://127.0.0.1/oauth2callback
  });

  let tokenResponse: Credentials;
  try {
    const { tokens } = await oauth2Client.getToken({
      code,
      redirect_uri: process.env.GOOGLE_REDIRECT_URI,
    });

    tokenResponse = tokens;
  } catch (err) {
    console.error("Failed to exchange code for tokens", err);
    return NextResponse.redirect("/unsuccessful");
  }

  // 4. Ensure all required Google Fit scopes were granted
  // The scope string returned by Google is space-delimited.
  const grantedScopes = (tokenResponse.scope ?? "").split(" ");
  const missingScopes = FIT_SCOPES.filter((scope) => !grantedScopes.includes(scope));

  if (missingScopes.length > 0) {
    console.warn("Missing scopes", missingScopes);
    return NextResponse.redirect("/unsuccessful");
  }

  // 5. Store the entire token object in a secure, HTTP-only cookie (development only)
  // NOTE: In production you should persist tokens in a database or encrypted store.
  cookieStore.set("oauth_tokens", JSON.stringify(tokenResponse), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });

  // 6. Clear the original CSRF state cookie
  cookieStore.set("oauth_state", "", { maxAge: 0, path: "/" });

  // Redirect back to the application root on success
  return NextResponse.redirect("/");
}

