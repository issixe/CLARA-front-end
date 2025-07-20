# CLARA Front-End

## Development & Production Ports

Both development (`npm run dev`) and production (`npm run start`) servers run on **port 5000**.

## Google OAuth Redirect URI

When configuring Google OAuth, set the authorised redirect URI to:

```
http://127.0.0.1:5000/oauth2callback
```

This uses the loopback address `127.0.0.1` instead of `localhost` to avoid Safari redirect issues.

## Environment Variables

Copy `.env.example` to `.env` and fill in the real secrets that you obtain from the Google Cloud Console:

```
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxx
OAUTHLIB_INSECURE_TRANSPORT=1   # dev only – allows HTTP for the OAuth flow.
```

`OAUTHLIB_INSECURE_TRANSPORT` must **never** be enabled in production. It is only present so that the OAuth flow will work over plain HTTP during local development.

## Switching Google Accounts During Development

If you need to sign in with a different Google account while developing, the existing cookies that Google sets for the loop-back origin (`127.0.0.1:5000`) can prevent the normal account-chooser screen from appearing. Clear the cookies for the origin first, then retry the sign-in flow.

Chrome / Edge:
1. Open DevTools (F12) ➜ Application tab ➜ Storage ➜ Cookies.
2. Select `http://127.0.0.1:5000` and click **Clear All**.

Safari:
1. Preferences ➜ Privacy ➜ **Manage Website Data…**
2. Search for `127.0.0.1` and remove the stored data.

Firefox:
1. Open the pad-lock icon in the address bar ➜ **Clear Cookies and Site Data**.

