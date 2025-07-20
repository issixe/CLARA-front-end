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
import requests
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()





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

# Vellum Configuration
VELLUM_API_KEY = os.getenv("VELLUM_API_KEY")
VELLUM_BASE_URL = "https://api.vellum.ai/v1"

# Check if Vellum is configured
if VELLUM_API_KEY:
    logging.info("Vellum API Key found")
else:
    logging.warning("VELLUM_API_KEY not found in environment variables")

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
    for s in sessions[:3]:           # print at most first 3 so log isn't huge
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


def _daily_heart_rate_summary(service, start_ms: int, end_ms: int):
    """Get daily heart rate summary statistics using the same approach as the working heart-rate endpoint."""
    try:
        # Get all heart rate points for the date range
        all_heart_rate_data = _get_heart_rate_points(service, start_ms, end_ms)
        
        # Group by date and calculate daily summaries
        daily_summaries = {}
        
        for point in all_heart_rate_data:
            # Convert timestamp to date
            date = dt.datetime.utcfromtimestamp(point["timestamp"] / 1000).date().isoformat()
            
            if date not in daily_summaries:
                daily_summaries[date] = []
            
            daily_summaries[date].append(point["value"])
        
        # Convert to the expected format
        daily = []
        for date, values in daily_summaries.items():
            if values:
                daily.append({
                    "date": date,
                    "average": round(sum(values) / len(values), 1),
                    "min": round(min(values), 1),
                    "max": round(max(values), 1),
                    "count": len(values)
                })
            else:
                daily.append({
                    "date": date,
                    "average": 0,
                    "min": 0,
                    "max": 0,
                    "count": 0
                })
        
        return daily
        
    except Exception as e:
        logging.warning("Heart rate data not available: %s", str(e))
        # Return empty data structure
        return []


def _daily_exercise_minutes(service, start_ms: int, end_ms: int):
    """Get daily exercise minutes (active minutes)."""
    try:
        body = {
            "aggregateBy": [{"dataTypeName": "com.google.active_minutes"}],
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
        
    except Exception as e:
        logging.warning("Exercise minutes data not available: %s", str(e))
        return []


def _daily_calories(service, start_ms: int, end_ms: int):
    """Get daily calories burned."""
    try:
        body = {
            "aggregateBy": [{"dataTypeName": "com.google.calories.expended"}],
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
                p.get("value", [{}])[0].get("fpVal", 0)
                for dataset in bucket.get("dataset", [])
                for p in dataset.get("point", [])
            )
            daily.append({"date": date, "value": round(total, 0)})
        return daily
        
    except Exception as e:
        logging.warning("Calories data not available: %s", str(e))
        return []


def _daily_distance(service, start_ms: int, end_ms: int):
    """Get daily distance traveled in meters."""
    try:
        body = {
            "aggregateBy": [{"dataTypeName": "com.google.distance.delta"}],
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
                p.get("value", [{}])[0].get("fpVal", 0)
                for dataset in bucket.get("dataset", [])
                for p in dataset.get("point", [])
            )
            daily.append({"date": date, "value": round(total, 0)})
        return daily
        
    except Exception as e:
        logging.warning("Distance data not available: %s", str(e))
        return []

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


@app.route("/api/comprehensive-report")
def comprehensive_report():
    """
    ?start=YYYY-MM-DD&end=YYYY-MM-DD  →  Comprehensive fitness data for Vellum reports.

    Example front-end fetch (on port 5001):
      fetch("http://127.0.0.1:5000/api/comprehensive-report?start=2025-07-01&end=2025-07-07")
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

    # 2️⃣  pull comprehensive fitness data
    start_date = start_dt.date()
    end_date = end_dt.date()
    
    # Basic metrics
    steps_daily = _daily_buckets(fitness, "com.google.step_count.delta", _millis(start_dt), _millis(end_dt))
    sleep_daily = _daily_sleep_minutes(fitness, _millis(start_dt), _millis(end_dt))
    
    # Enhanced metrics
    heart_rate_daily = _daily_heart_rate_summary(fitness, _millis(start_dt), _millis(end_dt))
    exercise_minutes_daily = _daily_exercise_minutes(fitness, _millis(start_dt), _millis(end_dt))
    calories_daily = _daily_calories(fitness, _millis(start_dt), _millis(end_dt))
    distance_daily = _daily_distance(fitness, _millis(start_dt), _millis(end_dt))

    # 3️⃣  fill gaps and ensure all dates are present
    steps_daily = _fill_gaps(steps_daily, start_date, end_date)
    sleep_daily = _fill_gaps(sleep_daily, start_date, end_date)
    exercise_minutes_daily = _fill_gaps(exercise_minutes_daily, start_date, end_date)
    calories_daily = _fill_gaps(calories_daily, start_date, end_date)
    distance_daily = _fill_gaps(distance_daily, start_date, end_date)
    
    # Special handling for heart rate data (has different structure)
    existing_hr = {d["date"]: d for d in heart_rate_daily}
    heart_rate_daily = []
    cur = start_date
    while cur <= end_date:
        iso = cur.isoformat()
        if iso in existing_hr:
            heart_rate_daily.append(existing_hr[iso])
        else:
            heart_rate_daily.append({
                "date": iso,
                "average": 0,
                "min": 0,
                "max": 0,
                "count": 0
            })
        cur += dt.timedelta(days=1)

    # 4️⃣  generate graphs
    steps_png = _plot_bars(steps_daily, "Steps", "Daily Step Count")
    sleep_png = _plot_bars(sleep_daily, "Minutes asleep", "Nightly Sleep Duration")
    exercise_png = _plot_bars(exercise_minutes_daily, "Minutes", "Daily Exercise Minutes")
    calories_png = _plot_bars(calories_daily, "Calories", "Daily Calories Burned")
    
    # Convert distance from meters to kilometers for display
    distance_km_daily = [{"date": d["date"], "value": round(d["value"] / 1000, 2)} for d in distance_daily]
    distance_png = _plot_bars(distance_km_daily, "Kilometers", "Daily Distance Traveled")

    # 5️⃣  save graphs to files
    steps_fname = f"steps_{start_str}_{end_str}.png"
    sleep_fname = f"sleep_{start_str}_{end_str}.png"
    exercise_fname = f"exercise_{start_str}_{end_str}.png"
    calories_fname = f"calories_{start_str}_{end_str}.png"
    distance_fname = f"distance_{start_str}_{end_str}.png"
    
    steps_path = os.path.join(app.static_folder, steps_fname)
    sleep_path = os.path.join(app.static_folder, sleep_fname)
    exercise_path = os.path.join(app.static_folder, exercise_fname)
    calories_path = os.path.join(app.static_folder, calories_fname)
    distance_path = os.path.join(app.static_folder, distance_fname)
    
    _write_bar_png(steps_daily, "Steps", "Daily Step Count", steps_path)
    _write_bar_png(sleep_daily, "Minutes asleep", "Nightly Sleep Duration", sleep_path)
    _write_bar_png(exercise_minutes_daily, "Minutes", "Daily Exercise Minutes", exercise_path)
    _write_bar_png(calories_daily, "Calories", "Daily Calories Burned", calories_path)
    _write_bar_png(distance_km_daily, "Kilometers", "Daily Distance Traveled", distance_path)
    
    NEXT_PUBLIC_DIR = Path(__file__).resolve().parent / "public" / "reports"
    NEXT_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    # copy (or symlink) into Next/public/reports
    import shutil
    shutil.copy2(steps_path, NEXT_PUBLIC_DIR / steps_fname)
    shutil.copy2(sleep_path, NEXT_PUBLIC_DIR / sleep_fname)
    shutil.copy2(exercise_path, NEXT_PUBLIC_DIR / exercise_fname)
    shutil.copy2(calories_path, NEXT_PUBLIC_DIR / calories_fname)
    shutil.copy2(distance_path, NEXT_PUBLIC_DIR / distance_fname)

    # 6️⃣  calculate summary statistics for Vellum
    def calculate_summary_stats(data_list, key="value"):
        if not data_list:
            return {"total": 0, "average": 0, "min": 0, "max": 0, "days_with_data": 0}
        
        values = [d[key] for d in data_list if d[key] > 0]
        days_with_data = len(values)
        
        if not values:
            return {"total": 0, "average": 0, "min": 0, "max": 0, "days_with_data": 0}
        
        return {
            "total": sum(values),
            "average": round(sum(values) / len(values), 1),
            "min": min(values),
            "max": max(values),
            "days_with_data": days_with_data
        }

    # 7️⃣  prepare comprehensive payload for Vellum
    payload = {
        "window": {"start": start_str, "end": end_str},
        "total_days": len(steps_daily),
        
        # Physical Activity Data
        "physical_activity": {
            "steps": {
                "daily_data": steps_daily,
                "summary": calculate_summary_stats(steps_daily),
                "graph": steps_png
            },
            "exercise_minutes": {
                "daily_data": exercise_minutes_daily,
                "summary": calculate_summary_stats(exercise_minutes_daily),
                "graph": exercise_png
            },
            "calories": {
                "daily_data": calories_daily,
                "summary": calculate_summary_stats(calories_daily),
                "graph": calories_png
            },
            "distance": {
                "daily_data": distance_km_daily,
                "summary": calculate_summary_stats(distance_km_daily),
                "graph": distance_png
            }
        },
        
        # Sleep Data
        "sleep": {
            "duration": {
                "daily_data": sleep_daily,
                "summary": calculate_summary_stats(sleep_daily),
                "graph": sleep_png
            },
            "heart_rate": {
                "daily_data": heart_rate_daily,
                "summary": {
                    "average_hr": round(sum(d["average"] for d in heart_rate_daily if d["average"] > 0) / max(1, len([d for d in heart_rate_daily if d["average"] > 0])), 1) if heart_rate_daily else 0,
                    "min_hr": min((d["min"] for d in heart_rate_daily if d["min"] > 0), default=0),
                    "max_hr": max((d["max"] for d in heart_rate_daily if d["max"] > 0), default=0),
                    "days_with_data": len([d for d in heart_rate_daily if d["average"] > 0])
                }
            }
        },
        
        # Overall Health Summary
        "health_summary": {
            "total_steps": sum(d["value"] for d in steps_daily) if steps_daily else 0,
            "total_exercise_minutes": sum(d["value"] for d in exercise_minutes_daily) if exercise_minutes_daily else 0,
            "total_calories": sum(d["value"] for d in calories_daily) if calories_daily else 0,
            "total_distance_km": sum(d["value"] for d in distance_km_daily) if distance_km_daily else 0,
            "total_sleep_hours": round(sum(d["value"] for d in sleep_daily) / 60, 1) if sleep_daily else 0,
            "average_sleep_hours": round(sum(d["value"] for d in sleep_daily) / (60 * len(sleep_daily)), 1) if sleep_daily else 0
        }
    }
    
    return jsonify(payload)


@app.route("/api/generate-vellum-reports", methods=["POST"])
def generate_vellum_reports():
    """
    Generate detailed physical activity and sleep reports using Vellum API.
    Expects comprehensive fitness data in request body.
    """
    try:
        data = request.get_json()
        if not data:
            abort(400, "No data provided")
        

        
        # Extract data from the comprehensive report
        window = data.get("window", {})
        physical_activity = data.get("physical_activity", {})
        sleep = data.get("sleep", {})
        health_summary = data.get("health_summary", {})
        
        # Prepare data for Vellum
        fitness_summary = {
            "date_range": f"{window.get('start', '')} to {window.get('end', '')}",
            "total_days": data.get("total_days", 0),
            "steps": {
                "total": health_summary.get("total_steps", 0),
                "average_per_day": physical_activity.get("steps", {}).get("summary", {}).get("average", 0),
                "days_with_data": physical_activity.get("steps", {}).get("summary", {}).get("days_with_data", 0)
            },
            "exercise": {
                "total_minutes": health_summary.get("total_exercise_minutes", 0),
                "average_per_day": physical_activity.get("exercise_minutes", {}).get("summary", {}).get("average", 0),
                "days_with_data": physical_activity.get("exercise_minutes", {}).get("summary", {}).get("days_with_data", 0)
            },
            "calories": {
                "total_burned": health_summary.get("total_calories", 0),
                "average_per_day": physical_activity.get("calories", {}).get("summary", {}).get("average", 0),
                "days_with_data": physical_activity.get("calories", {}).get("summary", {}).get("days_with_data", 0)
            },
            "distance": {
                "total_km": health_summary.get("total_distance_km", 0),
                "average_per_day": physical_activity.get("distance", {}).get("summary", {}).get("average", 0),
                "days_with_data": physical_activity.get("distance", {}).get("summary", {}).get("days_with_data", 0)
            },
            "sleep": {
                "total_hours": health_summary.get("total_sleep_hours", 0),
                "average_per_night": health_summary.get("average_sleep_hours", 0),
                "days_with_data": sleep.get("duration", {}).get("summary", {}).get("days_with_data", 0)
            },
            "heart_rate": {
                "average_resting": sleep.get("heart_rate", {}).get("summary", {}).get("average_hr", 0),
                "min_resting": sleep.get("heart_rate", {}).get("summary", {}).get("min_hr", 0),
                "max_resting": sleep.get("heart_rate", {}).get("summary", {}).get("max_hr", 0),
                "days_with_data": sleep.get("heart_rate", {}).get("summary", {}).get("days_with_data", 0)
            }
        }
        
        # Generate Physical Activity Report using Vellum
        physical_activity_report = generate_vellum_physical_activity_report(fitness_summary)
        physical_activity_report = _normalize_report(physical_activity_report)
        
        # Generate Sleep Report using Vellum
        sleep_report = generate_vellum_sleep_report(fitness_summary)
        sleep_report = _normalize_report(sleep_report)
        
        return jsonify({
            "physical_activity_report": physical_activity_report,
            "sleep_report": sleep_report,
            "generated_at": dt.datetime.now().isoformat(),
            "vellum_used": True,
            "analysis_type": "Vellum AI"
        })
        
    except Exception as e:
        logging.error("Error generating Vellum reports: %s", str(e))
        return jsonify({"error": str(e)}), 500


def _parse_vellum_template(template_str, data):
    """Parse Vellum template string and replace placeholders with actual data."""
    # Remove JSON code block markers if present
    template_str = template_str.strip('`').replace('```json\n', '').replace('\n```', '')
    
    # First replace all the direct value mappings
    replacements = {
        "{{date_range}}": data["date_range"],
        "{{total_steps}}": data["steps"]["total"],
        "{{avg_steps}}": data["steps"]["average_per_day"],
        "{{steps_days}}": data["steps"]["days_with_data"],
        "{{total_exercise}}": data["exercise"]["total_minutes"],
        "{{avg_exercise}}": data["exercise"]["average_per_day"],
        "{{exercise_days}}": data["exercise"]["days_with_data"],
        "{{total_calories}}": data["calories"]["total_burned"],
        "{{avg_calories}}": data["calories"]["average_per_day"],
        "{{calories_days}}": data["calories"]["days_with_data"],
        "{{total_distance}}": data["distance"]["total_km"],
        "{{avg_distance}}": data["distance"]["average_per_day"],
        "{{distance_days}}": data["distance"]["days_with_data"]
    }

    # Calculate activity level based on average steps
    avg_steps = data["steps"]["average_per_day"]
    if avg_steps >= 12500:
        activity_level = "Very Active"
        step_intensity = "high"
    elif avg_steps >= 7500:
        activity_level = "Moderately Active"
        step_intensity = "moderate"
    else:
        activity_level = "Lightly Active"
        step_intensity = "light"

    replacements["{{assessment}}"] = activity_level
    replacements["{{step_intensity}}"] = step_intensity

    # Replace placeholders with actual values
    result = template_str
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, str(value))

    # Extract JSON block if present first
    block_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", result)
    if block_match:
        result = block_match.group(1)
    else:
        # Fallback: attempt to find the first '{'...'}' span
        first_brace = result.find('{')
        last_brace = result.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            result = result[first_brace:last_brace+1]

    # Remove inline // comments which are invalid JSON
    result = re.sub(r"//.*?$", "", result, flags=re.MULTILINE)

    # Strip any lingering triple backticks or leading/trailing whitespace
    result = result.strip().strip('`')

    # Remove trailing commas before } or ]
    result = re.sub(r',\s*(?=[}\]])', '', result)

    # Attempt to parse JSON, with debug log on failure
    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        logging.error("Sanitized JSON that failed to parse:\n%s", result)
        raise

def generate_vellum_physical_activity_report(fitness_summary):
    """Generate physical activity report using Vellum API."""
    
    # Debug log the structure
    app.logger.debug("Fitness Summary Structure:")
    app.logger.debug(json.dumps(fitness_summary, indent=2))
    
    headers = {
        "X-API-Key": VELLUM_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "prompt_deployment_name": "fitness-report-deployment",
        "release_tag": "LATEST",
        "response_format": {
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "activity_level": {"type": "string"},
                    "summary": {
                        "type": "object",
                        "properties": {
                            "total_steps": {"type": "number"},
                            "total_exercise_minutes": {"type": "number"},
                            "total_calories_burned": {"type": "number"},
                            "total_distance_km": {"type": "number"},
                            "average_steps_per_day": {"type": "number"},
                            "average_exercise_minutes_per_day": {"type": "number"},
                            "average_calories_per_day": {"type": "number"},
                            "average_distance_per_day": {"type": "number"}
                        }
                    },
                    "insights": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "data_quality": {
                        "type": "object",
                        "properties": {
                            "days_with_step_data": {"type": "number"},
                            "days_with_exercise_data": {"type": "number"},
                            "days_with_calorie_data": {"type": "number"},
                            "days_with_distance_data": {"type": "number"}
                        }
                    }
                }
            }
        },
        "inputs": [
            {"type": "STRING", "name": "date_range", "value": fitness_summary['date_range']},
            {"type": "STRING", "name": "total_days", "value": str(fitness_summary['total_days'])},
            {"type": "STRING", "name": "total_steps", "value": str(fitness_summary['steps']['total'])},
            {"type": "STRING", "name": "avg_steps", "value": str(fitness_summary['steps']['average_per_day'])},
            {"type": "STRING", "name": "steps_days", "value": str(fitness_summary['steps']['days_with_data'])},
            {"type": "STRING", "name": "total_exercise", "value": str(fitness_summary['exercise']['total_minutes'])},
            {"type": "STRING", "name": "avg_exercise", "value": str(fitness_summary['exercise']['average_per_day'])},
            {"type": "STRING", "name": "exercise_days", "value": str(fitness_summary['exercise']['days_with_data'])},
            {"type": "STRING", "name": "total_calories", "value": str(fitness_summary['calories']['total_burned'])},
            {"type": "STRING", "name": "avg_calories", "value": str(fitness_summary['calories']['average_per_day'])},
            {"type": "STRING", "name": "calories_days", "value": str(fitness_summary['calories']['days_with_data'])},
            {"type": "STRING", "name": "total_distance", "value": str(fitness_summary['distance']['total_km'])},
            {"type": "STRING", "name": "avg_distance", "value": str(fitness_summary['distance']['average_per_day'])},
            {"type": "STRING", "name": "distance_days", "value": str(fitness_summary['distance']['days_with_data'])}
        ]
    }

    try:
        response = requests.post(
            "https://api.vellum.ai/v1/execute-prompt", 
            headers=headers, 
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("state") != "FULFILLED":
            raise Exception(f"Vellum API error: {result.get('error', {}).get('message', 'Unknown error')}")
            
        # Get the first output
        output = result["outputs"][0]
        app.logger.debug("Vellum raw output: %s", json.dumps(output, indent=2, default=str))

        # If Vellum already returned a JSON object, just return it
        if isinstance(output.get("value"), dict):
            return output["value"]
        
        # Otherwise treat it as a JSON template string
        template_str = output["value"]
        app.logger.debug("Template before replacements:\n%s", template_str)
        
        # Parse template and replace placeholders
        try:
            parsed = _parse_vellum_template(template_str, fitness_summary)
            return parsed
        except Exception as e:
            app.logger.error("Failed to parse template: %s", str(e))
            raise
        
    except Exception as e:
        app.logger.error(f"Vellum API error for physical activity report: {str(e)}")
        raise Exception(f"Failed to generate Vellum report: {str(e)}")


def generate_vellum_sleep_report(fitness_summary):
    """Generate sleep report using Vellum API."""
    if not VELLUM_API_KEY:
        raise Exception("Vellum API key not configured. Please set VELLUM_API_KEY environment variable.")
    headers = {
        "X-API-Key": VELLUM_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "prompt_deployment_name": "fitness-report-deployment",
        "release_tag": "LATEST",
        "response_format": {
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "sleep_quality": {"type": "string"},
                    "sleep_assessment": {"type": "string"},
                    "summary": {
                        "type": "object",
                        "properties": {
                            "total_sleep_hours": {"type": "number"},
                            "average_sleep_hours_per_night": {"type": "number"},
                            "average_resting_heart_rate": {"type": "number"},
                            "min_resting_heart_rate": {"type": "number"},
                            "max_resting_heart_rate": {"type": "number"}
                        }
                    },
                    "insights": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                    "data_quality": {
                        "type": "object",
                        "properties": {
                            "days_with_sleep_data": {"type": "number"},
                            "days_with_heart_rate_data": {"type": "number"}
                        }
                    }
                }
            }
        },
        "inputs": [
            {"type": "STRING", "name": "date_range", "value": fitness_summary['date_range']},
            {"type": "STRING", "name": "total_days", "value": str(fitness_summary['total_days'])},
            {"type": "STRING", "name": "total_sleep_hours", "value": str(fitness_summary['sleep']['total_hours'])},
            {"type": "STRING", "name": "avg_sleep_hours", "value": str(fitness_summary['sleep']['average_per_night'])},
            {"type": "STRING", "name": "sleep_days", "value": str(fitness_summary['sleep']['days_with_data'])},
            {"type": "STRING", "name": "avg_resting_hr", "value": str(fitness_summary['heart_rate']['average_resting'])},
            {"type": "STRING", "name": "min_resting_hr", "value": str(fitness_summary['heart_rate']['min_resting'])},
            {"type": "STRING", "name": "max_resting_hr", "value": str(fitness_summary['heart_rate']['max_resting'])},
            {"type": "STRING", "name": "hr_days", "value": str(fitness_summary['heart_rate']['days_with_data'])}
        ]
    }
    try:
        logging.info("Sending request to Vellum API: %s", json.dumps(payload, indent=2))
        response = requests.post(
            "https://api.vellum.ai/v1/execute-prompt",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            raise Exception(f"Vellum API error: {response.status_code} - {response.text}")
        
        result = response.json()
        logging.info("Received response from Vellum API: %s", json.dumps(result, indent=2))
        
        if result.get("state") == "REJECTED":
            raise Exception(f"Vellum API rejected: {result.get('error', {}).get('message', 'Unknown error')}")
        
        # Extract and parse the output value (mirrors physical-activity logic)
        if "outputs" not in result or len(result["outputs"]) == 0:
            raise Exception("No outputs found in Vellum response")

        output = result["outputs"][0]

        # If Vellum already returned a parsed JSON object
        if isinstance(output.get("value"), dict):
            return output["value"]

        template_str = output.get("value") or output.get("text", "")
        if not template_str:
            raise Exception("Vellum output was empty")

        # Try direct JSON parse first
        try:
            return json.loads(template_str)
        except json.JSONDecodeError:
            # Fall back to placeholder substitution / cleanup
            try:
                parsed = _parse_vellum_template(template_str, fitness_summary)
                return parsed
            except Exception as e:
                logging.error("Failed to parse template: %s", str(e))
                raise
        
    except Exception as e:
        logging.error("Vellum API error for sleep report: %s", str(e))
        raise Exception(f"Failed to generate Vellum report: {str(e)}")








def generate_physical_activity_report(window, physical_activity, health_summary):
    """Generate a detailed physical activity report using Vellum-style analysis."""
    
    steps = physical_activity.get("steps", {})
    exercise = physical_activity.get("exercise_minutes", {})
    calories = physical_activity.get("calories", {})
    distance = physical_activity.get("distance", {})
    
    steps_summary = steps.get("summary", {})
    exercise_summary = exercise.get("summary", {})
    calories_summary = calories.get("summary", {})
    distance_summary = distance.get("summary", {})
    
    # Calculate activity levels and trends
    avg_steps = steps_summary.get("average", 0)
    avg_exercise = exercise_summary.get("average", 0)
    avg_calories = calories_summary.get("average", 0)
    
    # Determine activity level
    if avg_steps >= 10000 and avg_exercise >= 30:
        activity_level = "Very Active"
    elif avg_steps >= 7500 or avg_exercise >= 20:
        activity_level = "Moderately Active"
    elif avg_steps >= 5000:
        activity_level = "Lightly Active"
    else:
        activity_level = "Sedentary"
    
    # Generate insights
    insights = []
    
    if steps_summary.get("days_with_data", 0) > 0:
        if avg_steps >= 10000:
            insights.append("Excellent step count! You're consistently meeting the recommended daily goal.")
        elif avg_steps >= 7500:
            insights.append("Good step count. Consider increasing to 10,000 steps for optimal health benefits.")
        else:
            insights.append("Consider increasing your daily step count to improve cardiovascular health.")
    
    if exercise_summary.get("days_with_data", 0) > 0:
        if avg_exercise >= 30:
            insights.append("Great job with exercise! You're meeting the recommended 30 minutes of daily activity.")
        elif avg_exercise >= 20:
            insights.append("Good exercise routine. Try to reach 30 minutes daily for maximum benefits.")
        else:
            insights.append("Consider adding more exercise to your daily routine for better health outcomes.")
    
    if calories_summary.get("days_with_data", 0) > 0:
        if avg_calories >= 2000:
            insights.append("High calorie burn indicates an active lifestyle.")
        elif avg_calories >= 1500:
            insights.append("Moderate calorie burn suggests good activity levels.")
        else:
            insights.append("Consider increasing physical activity to boost calorie burn.")
    
    # Generate recommendations
    recommendations = []
    
    if avg_steps < 10000:
        recommendations.append("Aim for 10,000 steps daily by taking short walks throughout the day.")
    
    if avg_exercise < 30:
        recommendations.append("Incorporate 30 minutes of moderate exercise into your daily routine.")
    
    if distance_summary.get("average", 0) < 5:  # less than 5km daily
        recommendations.append("Try to increase your daily distance through walking, running, or cycling.")
    
    if not recommendations:
        recommendations.append("Maintain your excellent activity levels and consider adding variety to your exercise routine.")
    
    return {
        "title": f"Physical Activity Report: {window.get('start', '')} to {window.get('end', '')}",
        "activity_level": activity_level,
        "summary": {
            "total_steps": health_summary.get("total_steps", 0),
            "total_exercise_minutes": health_summary.get("total_exercise_minutes", 0),
            "total_calories_burned": health_summary.get("total_calories", 0),
            "total_distance_km": health_summary.get("total_distance_km", 0),
            "average_steps_per_day": steps_summary.get("average", 0),
            "average_exercise_minutes_per_day": exercise_summary.get("average", 0),
            "average_calories_per_day": calories_summary.get("average", 0),
            "average_distance_per_day": distance_summary.get("average", 0)
        },
        "insights": insights,
        "recommendations": recommendations,
        "data_quality": {
            "days_with_step_data": steps_summary.get("days_with_data", 0),
            "days_with_exercise_data": exercise_summary.get("days_with_data", 0),
            "days_with_calorie_data": calories_summary.get("days_with_data", 0),
            "days_with_distance_data": distance_summary.get("days_with_data", 0)
        }
    }


def generate_sleep_report(window, sleep, health_summary):
    """Generate a detailed sleep report using Vellum-style analysis."""
    
    sleep_duration = sleep.get("duration", {})
    heart_rate = sleep.get("heart_rate", {})
    
    duration_summary = sleep_duration.get("summary", {})
    hr_summary = heart_rate.get("summary", {})
    
    # Calculate sleep metrics
    avg_sleep_hours = health_summary.get("average_sleep_hours", 0)
    total_sleep_hours = health_summary.get("total_sleep_hours", 0)
    
    # Determine sleep quality
    if avg_sleep_hours >= 7 and avg_sleep_hours <= 9:
        sleep_quality = "Excellent"
        sleep_assessment = "You're getting the recommended amount of sleep for optimal health."
    elif avg_sleep_hours >= 6 and avg_sleep_hours < 7:
        sleep_quality = "Good"
        sleep_assessment = "Your sleep duration is close to optimal. Consider adding 30-60 minutes for better recovery."
    elif avg_sleep_hours >= 5 and avg_sleep_hours < 6:
        sleep_quality = "Fair"
        sleep_assessment = "You're getting less sleep than recommended. This may impact your health and performance."
    else:
        sleep_quality = "Poor"
        sleep_assessment = "Your sleep duration is significantly below recommended levels. Consider prioritizing sleep hygiene."
    
    # Generate sleep insights
    insights = []
    
    if avg_sleep_hours >= 8:
        insights.append("Excellent sleep duration! You're getting the recommended 7-9 hours of sleep.")
    elif avg_sleep_hours >= 7:
        insights.append("Good sleep duration. You're close to the optimal range for most adults.")
    elif avg_sleep_hours >= 6:
        insights.append("Moderate sleep duration. Consider extending your sleep time for better recovery.")
    else:
        insights.append("Your sleep duration is below recommended levels. This may affect your health and daily performance.")
    
    # Heart rate insights during sleep
    if hr_summary.get("days_with_data", 0) > 0:
        avg_hr = hr_summary.get("average_hr", 0)
        if avg_hr > 0:
            if avg_hr < 60:
                insights.append("Your resting heart rate is excellent, indicating good cardiovascular fitness.")
            elif avg_hr < 70:
                insights.append("Your resting heart rate is good, suggesting healthy cardiovascular function.")
            else:
                insights.append("Consider discussing your resting heart rate with a healthcare provider.")
    
    # Generate sleep recommendations
    recommendations = []
    
    if avg_sleep_hours < 7:
        recommendations.append("Aim for 7-9 hours of sleep per night for optimal health and recovery.")
        recommendations.append("Establish a consistent sleep schedule and bedtime routine.")
        recommendations.append("Create a sleep-friendly environment: dark, quiet, and cool.")
    
    if avg_sleep_hours > 9:
        recommendations.append("While you're getting plenty of sleep, excessive sleep may indicate underlying health issues.")
    
    if duration_summary.get("days_with_data", 0) < 3:
        recommendations.append("Consider tracking your sleep more consistently to get better insights.")
    
    if not recommendations:
        recommendations.append("Maintain your excellent sleep habits and continue prioritizing rest and recovery.")
    
    return {
        "title": f"Sleep Report: {window.get('start', '')} to {window.get('end', '')}",
        "sleep_quality": sleep_quality,
        "sleep_assessment": sleep_assessment,
        "summary": {
            "total_sleep_hours": total_sleep_hours,
            "average_sleep_hours_per_night": avg_sleep_hours,
            "average_resting_heart_rate": hr_summary.get("average_hr", 0),
            "min_resting_heart_rate": hr_summary.get("min_hr", 0),
            "max_resting_heart_rate": hr_summary.get("max_hr", 0)
        },
        "insights": insights,
        "recommendations": recommendations,
        "data_quality": {
            "days_with_sleep_data": duration_summary.get("days_with_data", 0),
            "days_with_heart_rate_data": hr_summary.get("days_with_data", 0)
        }
    }


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


def _convert_numeric(value):
    """Try to convert string numbers to int or float."""
    if isinstance(value, str):
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    return value


def _normalize_report(report: dict):
    """Recursively walk report and convert numeric strings to numbers for frontend compatibility."""
    if isinstance(report, dict):
        return {k: _normalize_report(v) for k, v in report.items()}
    if isinstance(report, list):
        return [_normalize_report(v) for v in report]
    return _convert_numeric(report)




if __name__ == "__main__":
    app.run(host=BACKEND_HOST, port=BACKEND_PORT, debug=True)

