"""Minimal Flask API shim exposing only the Google OAuth endpoints
required by the React front-end.

Runs on the SAME port (5000) as the development server, so start it
*before* `npm run dev` and proxy non-API requests back to Next.js.

Usage (dev):
  python3 -m venv venv && source venv/bin/activate
  pip install flask google-auth google-auth-oauthlib
  # make sure client_secret.json is in the repo root
  python app.py

The script does *only*:
  • GET /authorize        – start Google OAuth flow
  • GET /oauth2callback   – finish OAuth, store tokens in Flask session
  • GET /tokens           – JSON tokens (so React can read them if needed)
  • GET /logout           – clear session
All other paths are proxied to the running Next dev server on 127.0.0.1:5001
(or wherever you start it).
"""

from __future__ import annotations

import json
import os
from urllib.parse import urljoin
import base64
import datetime as dt
import io
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import matplotlib
matplotlib.use("Agg")          # head-less
import matplotlib.pyplot as plt
from flask import Flask, abort, redirect, request, session, url_for, jsonify
from google_auth_oauthlib.flow import Flow
from werkzeug.middleware.proxy_fix import ProxyFix
import requests
from google.oauth2.credentials import Credentials
import logging
logging.basicConfig(level=logging.DEBUG, format="DBG %(message)s")
from pathlib import Path
from flask_cors import CORS





# ──────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1") # allow extra scopes
CLIENT_SECRETS_FILE = "client_secret.json"  # must exist in repo root
FRONTEND_ORIGIN = "http://127.0.0.1:5001/logs"  # where `npm run dev` serves React
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 5000  # flask port

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.location.read",
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
]

os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")  # dev-only

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")
CORS(
    app,
    origins=["http://127.0.0.1:5001"],
    supports_credentials=True   # because you send the session cookie
)


# ──────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────

def build_flow(state: str | None = None) -> Flow:
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for("oauth2callback", _external=True),
    )

def _daily_sleep_minutes(service, start_ms: int, end_ms: int):
    """Same as before but with verbose prints so we can see what the API returns."""
    iso = lambda ms: dt.datetime.utcfromtimestamp(ms / 1000).isoformat() + "Z"

    logging.debug("--------- SLEEP DEBUG ---------")
    logging.debug("Query window  : %s  →  %s", iso(start_ms), iso(end_ms))

    # ① list sleep *sessions* (activityType 72) --------------------
    sess_resp = service.users().sessions().list(
        userId="me",
        startTime=iso(start_ms),
        endTime=iso(end_ms),
        activityType=72,      # sleep sessions
    ).execute()

    sessions = sess_resp.get("session", [])
    logging.debug("Sessions found: %s", len(sessions))
    for s in sessions[:3]:           # print at most first 3 so log isn’t huge
        logging.debug("  • %s → %s  (%s)",
                      s["startTimeMillis"], s["endTimeMillis"],
                      s.get("name", "no name"))

    if not sessions:
        logging.debug("!! Google Fit returned ZERO sleep sessions.")

    # ② bucket minutes per calendar date --------------------------
    totals = {}
    for s in sessions:
        s_start = int(s["startTimeMillis"]);  s_end = int(s["endTimeMillis"])
        cur = s_start
        while cur < s_end:
            day_start = dt.datetime.utcfromtimestamp(cur / 1000).date()
            next_midnight = (
                dt.datetime.combine(day_start, dt.time.min, tzinfo=dt.timezone.utc)
                + dt.timedelta(days=1)
            )
            segment_end = min(s_end, int(next_midnight.timestamp() * 1000))
            mins = (segment_end - cur) // 60000
            totals[day_start.isoformat()] = totals.get(day_start.isoformat(), 0) + mins
            cur = segment_end

    logging.debug("Daily totals  : %s", totals)
    logging.debug("--------- /SLEEP DEBUG --------")

    return [{"date": d, "value": totals[d]} for d in sorted(totals)]

def _fill_gaps(daily: list[dict], start: dt.date, end: dt.date):
    """
    Ensure every date between start-end (inclusive) appears exactly once.
    Missing dates get value 0.  Input & output order is chronological.
    """
    existing = {d["date"]: d["value"] for d in daily}
    filled = []
    cur = start
    while cur <= end:
        iso = cur.isoformat()
        filled.append({"date": iso, "value": existing.get(iso, 0)})
        cur += dt.timedelta(days=1)
    return filled

def _write_bar_png(daily, y_label: str, title: str, out_path: str):
    """Builds a bar chart and writes it straight to `out_path`."""
    dates = [d["date"] for d in daily]
    values = [d["value"] for d in daily]

    fig, ax = plt.subplots(figsize=(max(6, len(dates) * 0.4), 4))
    ax.bar(dates, values)
    ax.set_xlabel("Date")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    fig.autofmt_xdate(rotation=45, ha="right")

    # ensure parent dir exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# ──────────────────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────────────────

@app.route("/authorize")
def authorize():
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["state"] = state
    return redirect(auth_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = session.get("state")
    if not state or request.args.get("state") != state:
        abort(400, "state mismatch")

    flow = build_flow(state)
    flow.fetch_token(authorization_response=request.url)
    session["tokens"] = json.loads(flow.credentials.to_json())
    return redirect(FRONTEND_ORIGIN)  # back to React


@app.route("/tokens")
def tokens():
    """Simple JSON endpoint so React can poll for tokens if needed."""
    return jsonify(session.get("tokens"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(FRONTEND_ORIGIN)


@app.route("/<path:rest>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy_to_frontend(rest: str):
    """Proxy any unknown path to the React dev server so the SPA keeps working."""
    proxied_url = urljoin(FRONTEND_ORIGIN + "/", rest)
    if request.query_string:
        proxied_url += "?" + request.query_string.decode()

    resp = requests.request(
        request.method,
        proxied_url,
        headers={key: value for key, value in request.headers if key != "Host"},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
    )

    excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    headers = [(name, value) for name, value in resp.raw.headers.items() if name.lower() not in excluded]
    response = app.response_class(resp.content, resp.status_code, headers)
    return response

def _millis(ts: dt.datetime) -> int:
    """UTC → epoch millis"""
    return int(ts.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)

def _daily_buckets(service, data_type: str, start_ms: int, end_ms: int):
    """Call Fitness aggregate endpoint and return [{date, value}] per day."""
    body = {
        "aggregateBy": [{"dataTypeName": data_type}],
        "bucketByTime": {"durationMillis": 86_400_000},
        "startTimeMillis": start_ms,
        "endTimeMillis": end_ms,
    }
    resp = (
        service.users()
        .dataset()
        .aggregate(userId="me", body=body)
        .execute()
    )

    daily = []
    for bucket in resp.get("bucket", []):
        date = dt.datetime.fromtimestamp(int(bucket["startTimeMillis"]) / 1000, tz=dt.timezone.utc).date().isoformat()
        total = sum(
            p.get("value", [{}])[0].get("intVal", 0)
            for dataset in bucket.get("dataset", [])
            for p in dataset.get("point", [])
        )
        daily.append({"date": date, "value": total})
    return daily

def _plot_bars(daily, y_label, title):
    """Return base-64 PNG bar chart for the [{date,value}] list passed in."""
    dates = [d["date"] for d in daily]
    values = [d["value"] for d in daily]

    fig, ax = plt.subplots(figsize=(max(6, len(dates) * 0.4), 4))
    ax.bar(dates, values)
    ax.set_xlabel("Date")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    fig.autofmt_xdate(rotation=45, ha="right")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")

# ────────────────────────────────────────────────────────────
@app.route("/api/report")
def report():
    """
    ?start=YYYY-MM-DD&end=YYYY-MM-DD  →  JSON for Vellum + base-64 graphs.

    Example front-end fetch (on port 5001):
      fetch("http://127.0.0.1:5000/api/report?start=2025-07-01&end=2025-07-07")
    """
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    if not (start_str and end_str):
        abort(400, "start and end query parameters are required (YYYY-MM-DD)")

    start_dt = dt.datetime.strptime(start_str, "%Y-%m-%d")
    # inclusive: extend to end-of-day
    end_dt = dt.datetime.strptime(end_str, "%Y-%m-%d") + dt.timedelta(days=1) - dt.timedelta(milliseconds=1)

    # 1️⃣  rebuild credentials from the session and refresh if needed
    tokens = session.get("tokens")
    if not tokens:
        abort(401, "not authenticated")
    if isinstance(tokens.get("expiry"), str):
        exp = dt.datetime.fromisoformat(tokens["expiry"].replace("Z", "+00:00"))
        tokens["expiry"] = exp.replace(tzinfo=None)     # ← make UTC-naive
    creds = Credentials(**tokens)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session["tokens"] = json.loads(creds.to_json())  # keep fresh

    fitness = build("fitness", "v1", credentials=creds, cache_discovery=False)

    # 2️⃣  pull daily buckets
    steps_daily = _daily_buckets(
        fitness,
        "com.google.step_count.delta",
        _millis(start_dt),
        _millis(end_dt),
    )
    sleep_daily = _daily_sleep_minutes(
        fitness,
        _millis(start_dt),
        _millis(end_dt),
    )    

    # 3️⃣  graphs
    start_date = start_dt.date()
    end_date   = end_dt.date()
    steps_daily = _fill_gaps(steps_daily, start_date, end_date)
    sleep_daily = _fill_gaps(sleep_daily, start_date, end_date)
    steps_png = _plot_bars(steps_daily, "Steps", "Daily Step Count")
    sleep_png = _plot_bars(sleep_daily, "Minutes asleep", "Nightly Sleep Duration")
    steps_fname = f"steps_{start_str}_{end_str}.png"
    sleep_fname = f"sleep_{start_str}_{end_str}.png"
    steps_path = os.path.join(app.static_folder, steps_fname)
    sleep_path = os.path.join(app.static_folder, sleep_fname)
    _write_bar_png(steps_daily, "Steps", "Daily Step Count", steps_path)
    _write_bar_png(sleep_daily, "Minutes asleep", "Nightly Sleep Duration", sleep_path)
    NEXT_PUBLIC_DIR = Path(__file__).resolve().parent / "public" / "reports"
    NEXT_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    # copy (or symlink) into Next/public/reports
    import shutil
    shutil.copy2(steps_path, NEXT_PUBLIC_DIR / steps_fname)
    shutil.copy2(sleep_path, NEXT_PUBLIC_DIR / sleep_fname)
    # 4️⃣  LLM-friendly JSON payload
    payload = {
        "window": {"start": start_str, "end": end_str},
        "physical_activity_data": steps_daily,
        "sleep_data": sleep_daily,
    }
    return jsonify(payload)




# ──────────────────────────────────────────────────────────────────────
# TEST PAGE – simple HTML front-end served by Flask
# URL: http://127.0.0.1:5000/report-test
# ──────────────────────────────────────────────────────────────────────
TEST_PAGE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Fit Report Tester</title>
  <style>
    body{font-family:system-ui,sans-serif;margin:2rem;max-width:60ch}
    input{padding:.3rem .4rem;margin-right:.5rem}
    button{padding:.4rem .8rem}
    img{max-width:100%;margin-top:1rem;border:1px solid #ddd}
    pre{background:#f5f5f5;padding:1rem;overflow:auto}
  </style>
</head>
<body>
  <h1>Google Fit Report tester</h1>

  <p>Select a date range, then click <b>Fetch report</b>.  
     You must be logged in (session cookie present) because the page
     calls <code>/api/report</code> under the hood.</p>

  <label>Start date
    <input type="date" id="start" />
  </label>
  <label>End date
    <input type="date" id="end" />
  </label>
  <button id="go">Fetch report</button>

  <h2>Graphs</h2>
  <img id="steps" alt="Step graph will appear here"/>
  <img id="sleep" alt="Sleep graph will appear here"/>

  <h2>Raw JSON</h2>
  <pre id="json">(waiting…)</pre>

<script>
document.getElementById("go").onclick = async () => {
  const s = document.getElementById("start").value;
  const e = document.getElementById("end").value;
  if (!s || !e) { alert("Pick both dates"); return; }

  const resp = await fetch(`/api/report?start=${s}&end=${e}`, {
    credentials: "include"
  });
  if (!resp.ok) {
    document.getElementById("json").textContent =
      `Error ${resp.status}: ${await resp.text()}`;
    return;
  }

  const data = await resp.json();
  document.getElementById("steps").src =
    `data:image/png;base64,${data.graphs.steps_png_base64}`;
  document.getElementById("sleep").src =
    `data:image/png;base64,${data.graphs.sleep_png_base64}`;
  document.getElementById("json").textContent =
    JSON.stringify(data, null, 2);
};
</script>
</body>
</html>
"""

@app.route("/report-test")
def report_test():
    """Very small HTML page that lets you hit /api/report from the browser."""
    return TEST_PAGE_HTML



if __name__ == "__main__":
    app.run(host=BACKEND_HOST, port=BACKEND_PORT, debug=True)

