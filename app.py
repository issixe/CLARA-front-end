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


@app.route("/api/rings")
def rings():
    """
    ?date=YYYY-MM-DD  →  JSON with sleep and energy data for ring display.

    Example front-end fetch (on port 5001):
      fetch("http://127.0.0.1:5000/api/rings?date=2025-07-19")
    """
    date_str = request.args.get("date")
    if not date_str:
        abort(400, "date query parameter is required (YYYY-MM-DD)")

    date_dt = dt.datetime.strptime(date_str, "%Y-%m-%d")
    start_dt = date_dt
    end_dt = date_dt + dt.timedelta(days=1) - dt.timedelta(milliseconds=1)

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

    # 2️⃣  pull sleep data for the specific date
    sleep_daily = _daily_sleep_minutes(
        fitness,
        _millis(start_dt),
        _millis(end_dt),
    )
    
    # 3️⃣  pull step data for the specific date
    steps_daily = _daily_buckets(
        fitness,
        "com.google.step_count.delta",
        _millis(start_dt),
        _millis(end_dt),
    )

    # 4️⃣  extract values for the specific date
    sleep_minutes = sleep_daily[0]["value"] if sleep_daily else 0
    sleep_hours = sleep_minutes / 60.0
    
    steps_count = steps_daily[0]["value"] if steps_daily else 0

    # 5️⃣  define goals (these could be configurable)
    sleep_goal_hours = 8.0
    steps_goal = 10000

    # 6️⃣  return ring data
    payload = {
        "date": date_str,
        "sleep": {
            "current": round(sleep_hours, 1),
            "goal": sleep_goal_hours,
            "percentage": min(round((sleep_hours / sleep_goal_hours) * 100), 100)
        },
        "steps": {
            "current": steps_count,
            "goal": steps_goal,
            "percentage": min(round((steps_count / steps_goal) * 100), 100)
        }
    }
    
    return jsonify(payload)


@app.route("/api/heart-rate")
def heart_rate():
    """
    ?date=YYYY-MM-DD  →  JSON with heart rate data and base64 graph.

    Example front-end fetch (on port 5001):
      fetch("http://127.0.0.1:5000/api/heart-rate?date=2025-07-19")
    """
    date_str = request.args.get("date")
    if not date_str:
        abort(400, "date query parameter is required (YYYY-MM-DD)")

    date_dt = dt.datetime.strptime(date_str, "%Y-%m-%d")
    start_dt = date_dt
    end_dt = date_dt + dt.timedelta(days=1) - dt.timedelta(milliseconds=1)

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

    # 2️⃣  pull heart rate data points for the specific date
    heart_rate_data = _get_heart_rate_points(
        fitness,
        _millis(start_dt),
        _millis(end_dt),
    )

    # 3️⃣  generate heart rate graph
    heart_rate_png = _plot_heart_rate(heart_rate_data, date_str)

    # 4️⃣  calculate summary statistics
    if heart_rate_data:
        values = [point["value"] for point in heart_rate_data]
        avg_hr = sum(values) / len(values)
        min_hr = min(values)
        max_hr = max(values)
    else:
        avg_hr = min_hr = max_hr = 0

    # 5️⃣  return heart rate data
    payload = {
        "date": date_str,
        "data_points": heart_rate_data,
        "summary": {
            "average": round(avg_hr, 1),
            "min": min_hr,
            "max": max_hr,
            "count": len(heart_rate_data)
        },
        "graph": heart_rate_png
    }
    
    return jsonify(payload)


def _get_heart_rate_points(service, start_ms: int, end_ms: int):
    """Get individual heart rate data points for detailed analysis."""
    iso = lambda ms: dt.datetime.utcfromtimestamp(ms / 1000).isoformat() + "Z"
    
    logging.debug("--------- HEART RATE DEBUG ---------")
    logging.debug("Query window  : %s  →  %s", iso(start_ms), iso(end_ms))

    heart_rate_data = []
    
    # Try using the aggregate endpoint first (most reliable)
    try:
        logging.debug("Trying aggregate heart rate endpoint...")
        aggregate_resp = service.users().dataset().aggregate(
            userId="me",
            body={
                "aggregateBy": [{"dataTypeName": "com.google.heart_rate.bpm"}],
                "bucketByTime": {"durationMillis": 1800000},  # 30 minute buckets for more detail
                "startTimeMillis": start_ms,
                "endTimeMillis": end_ms,
            }
        ).execute()
        
        logging.debug("Aggregate heart rate response: %s", aggregate_resp)
        
        for bucket in aggregate_resp.get("bucket", []):
            for dataset in bucket.get("dataset", []):
                for point in dataset.get("point", []):
                    # Handle different timestamp formats
                    timestamp = 0
                    if "startTimeMillis" in point:
                        timestamp = int(point["startTimeMillis"])
                    elif "startTimeNanos" in point:
                        timestamp = int(point["startTimeNanos"]) // 1_000_000  # Convert to milliseconds
                    
                    # Try different value field names
                    value = 0
                    if point.get("value"):
                        # Handle array of values - take the first one
                        value_obj = point["value"][0]
                        value = value_obj.get("fpVal", value_obj.get("intVal", 0))
                    
                    # Convert to local time for display
                    if timestamp > 0:
                        utc_time = dt.datetime.utcfromtimestamp(timestamp / 1000)
                        local_time = utc_time.strftime("%H:%M")
                        
                        heart_rate_data.append({
                            "time": local_time,
                            "timestamp": timestamp,
                            "value": value
                        })
        
        logging.debug("Aggregate method found %s heart rate points", len(heart_rate_data))
        
    except Exception as e:
        logging.debug("Aggregate heart rate failed: %s", str(e))
        
        # Fallback: try to list data sources and use specific ones
        try:
            data_sources_resp = service.users().dataSources().list(userId="me").execute()
            heart_rate_sources = []
            
            for ds in data_sources_resp.get("dataSource", []):
                if "heart_rate" in ds.get("dataType", {}).get("name", "").lower():
                    heart_rate_sources.append({
                        "id": ds.get("dataStreamId", "unknown"),  # Use dataStreamId
                        "name": ds.get("dataType", {}).get("name", "unknown"),
                        "type": ds.get("type", "unknown")
                    })
                    logging.debug("Found heart rate source: %s (%s)", ds.get("dataStreamId"), ds.get("dataType", {}).get("name"))
            
            logging.debug("Available heart rate sources: %s", heart_rate_sources)
            
            # Try each heart rate source
            for source in heart_rate_sources:
                if heart_rate_data:  # If we already have data, skip
                    break
                    
                try:
                    logging.debug("Trying heart rate source: %s", source["id"])
                    resp = service.users().dataSources().datasets().get(
                        userId="me",
                        dataSourceId=source["id"],
                        datasetId=f"{start_ms}-{end_ms}",
                    ).execute()
                    
                    points = resp.get("point", [])
                    logging.debug("Source %s found %s points", source["id"], len(points))
                    
                    for point in points:
                        timestamp = int(point["startTimeNanos"]) // 1_000_000  # Convert to milliseconds
                        # Try different value field names
                        value = 0
                        if point.get("value"):
                            value_obj = point["value"][0]
                            value = value_obj.get("fpVal", value_obj.get("intVal", 0))
                        
                        # Convert to local time for display
                        utc_time = dt.datetime.utcfromtimestamp(timestamp / 1000)
                        local_time = utc_time.strftime("%H:%M")
                        
                        heart_rate_data.append({
                            "time": local_time,
                            "timestamp": timestamp,
                            "value": value
                        })
                        
                except Exception as e2:
                    logging.debug("Source %s failed: %s", source["id"], str(e2))
        
        except Exception as e3:
            logging.debug("Failed to list data sources: %s", str(e3))
    
    logging.debug("Final result: %s heart rate points", len(heart_rate_data))
    logging.debug("--------- /HEART RATE DEBUG --------")
    
    return heart_rate_data


def _plot_heart_rate(heart_rate_data, date_str):
    """Create a line graph of heart rate fluctuations throughout the day."""
    if not heart_rate_data:
        # Return empty graph if no data
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No heart rate data available', 
                ha='center', va='center', transform=ax.transAxes,
                fontsize=14, color='gray')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    # Extract data for plotting
    times = [point["time"] for point in heart_rate_data]
    values = [point["value"] for point in heart_rate_data]

    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot heart rate line
    ax.plot(range(len(times)), values, color='#dc2626', linewidth=2, marker='o', markersize=4)
    
    # Customize the plot
    ax.set_xlabel('Time of Day', fontsize=12, fontweight='bold')
    ax.set_ylabel('Heart Rate (BPM)', fontsize=12, fontweight='bold')
    ax.set_title(f'Heart Rate Fluctuations - {date_str}', fontsize=14, fontweight='bold')
    
    # Set x-axis ticks to show time labels
    if len(times) > 0:
        # Show every nth time label to avoid crowding
        n = max(1, len(times) // 8)
        tick_positions = list(range(0, len(times), n))
        tick_labels = [times[i] for i in tick_positions]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right')
    
    # Add grid for better readability
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Set y-axis limits with some padding
    if values:
        min_val = min(values)
        max_val = max(values)
        padding = (max_val - min_val) * 0.1 if max_val > min_val else 10
        ax.set_ylim(max(0, min_val - padding), max_val + padding)
    
    # Add average line
    if values:
        avg_hr = sum(values) / len(values)
        ax.axhline(y=avg_hr, color='#f97316', linestyle='--', alpha=0.7, 
                  label=f'Average: {avg_hr:.1f} BPM')
        ax.legend()
    
    # Style improvements
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Adjust layout
    plt.tight_layout()
    
    # Convert to base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100, 
                facecolor='white', edgecolor='none')
    plt.close(fig)
    
    return base64.b64encode(buf.getvalue()).decode("ascii")


@app.route("/api/debug/sources")
def debug_sources():
    """Debug endpoint to list all available data sources."""
    tokens = session.get("tokens")
    if not tokens:
        abort(401, "not authenticated")
    
    if isinstance(tokens.get("expiry"), str):
        exp = dt.datetime.fromisoformat(tokens["expiry"].replace("Z", "+00:00"))
        tokens["expiry"] = exp.replace(tzinfo=None)
    creds = Credentials(**tokens)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session["tokens"] = json.loads(creds.to_json())

    fitness = build("fitness", "v1", credentials=creds, cache_discovery=False)
    
    try:
        data_sources_resp = fitness.users().dataSources().list(userId="me").execute()
        sources = []
        
        logging.debug("Raw data sources response: %s", data_sources_resp)
        
        for ds in data_sources_resp.get("dataSource", []):
            try:
                # Debug: print the raw data source to see its structure
                logging.debug("Raw data source: %s", ds)
                
                source_info = {
                    "id": ds.get("dataStreamId", "unknown"),  # Use dataStreamId instead of dataSourceId
                    "name": ds.get("dataType", {}).get("name", "unknown"),
                    "type": ds.get("type", "unknown"),
                    "device": ds.get("device", {}).get("model", "Unknown")
                }
                sources.append(source_info)
                logging.debug("Processed source: %s", source_info)
            except Exception as e:
                logging.debug("Error processing source %s: %s", ds, str(e))
                sources.append({
                    "id": "error",
                    "name": "error_processing",
                    "type": "error",
                    "device": "Unknown",
                    "raw_data": str(ds)
                })
        
        heart_rate_sources = []
        for s in sources:
            if "heart_rate" in s["name"].lower():
                heart_rate_sources.append(s)
        
        return jsonify({
            "total_sources": len(sources),
            "sources": sources,
            "heart_rate_sources": heart_rate_sources,
            "raw_response": data_sources_resp
        })
        
    except Exception as e:
        logging.debug("Debug sources error: %s", str(e))
        return jsonify({"error": str(e), "traceback": str(e.__traceback__)})


@app.route("/api/debug/test")
def debug_test():
    """Simple test endpoint to verify field extraction."""
    tokens = session.get("tokens")
    if not tokens:
        abort(401, "not authenticated")
    
    if isinstance(tokens.get("expiry"), str):
        exp = dt.datetime.fromisoformat(tokens["expiry"].replace("Z", "+00:00"))
        tokens["expiry"] = exp.replace(tzinfo=None)
    creds = Credentials(**tokens)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session["tokens"] = json.loads(creds.to_json())

    fitness = build("fitness", "v1", credentials=creds, cache_discovery=False)
    
    try:
        data_sources_resp = fitness.users().dataSources().list(userId="me").execute()
        
        # Test with first heart rate source
        heart_rate_sources = []
        for ds in data_sources_resp.get("dataSource", []):
            if "heart_rate" in ds.get("dataType", {}).get("name", "").lower():
                heart_rate_sources.append(ds)
        
        if heart_rate_sources:
            test_source = heart_rate_sources[0]
            return jsonify({
                "test_source": test_source,
                "dataStreamId": test_source.get("dataStreamId"),
                "dataSourceId": test_source.get("dataSourceId"),
                "all_keys": list(test_source.keys())
            })
        else:
            return jsonify({"error": "No heart rate sources found"})
        
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/debug/heart-test")
def debug_heart_test():
    """Test heart rate with a specific known data stream ID."""
    tokens = session.get("tokens")
    if not tokens:
        abort(401, "not authenticated")
    
    if isinstance(tokens.get("expiry"), str):
        exp = dt.datetime.fromisoformat(tokens["expiry"].replace("Z", "+00:00"))
        tokens["expiry"] = exp.replace(tzinfo=None)
    creds = Credentials(**tokens)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session["tokens"] = json.loads(creds.to_json())

    fitness = build("fitness", "v1", credentials=creds, cache_discovery=False)
    
    try:
        # Test with June 14, 2025 (when user mentioned they have heart rate data)
        test_date = dt.date(2025, 6, 14)
        start_ms = _millis(dt.datetime.combine(test_date, dt.time.min))
        end_ms = _millis(dt.datetime.combine(test_date, dt.time.max))
        
        # Try the specific data stream ID we know exists
        test_stream_id = "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
        
        try:
            resp = fitness.users().dataSources().datasets().get(
                userId="me",
                dataSourceId=test_stream_id,
                datasetId=f"{start_ms}-{end_ms}",
            ).execute()
            
            return jsonify({
                "success": True,
                "dataStreamId": test_stream_id,
                "response": resp,
                "points_count": len(resp.get("point", [])),
                "points": resp.get("point", [])[:3]  # First 3 points for inspection
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "dataStreamId": test_stream_id,
                "error": str(e)
            })
        
    except Exception as e:
        return jsonify({"error": str(e)})


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

