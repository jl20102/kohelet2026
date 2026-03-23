from flask import Flask, render_template, request, jsonify
import requests
import urllib.parse
import numpy as np
import math
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import io
import base64
from collections import deque

app = Flask(__name__)

# speed_history stores 1 for active, 0 for idle (2-second intervals)
speed_history = deque(maxlen=10)
checkin_history = deque(maxlen=50)

# Anxiety-specific state
anxiety_list = []
check_in_intervals = []


# ---------------------------------------------------------------------------
# Anxiety Logic (ported from standalone module)
# ---------------------------------------------------------------------------

def calculate_next_anxiety_check(anxiety_list: list, average_scroll_speed: float) -> float:
    """
    Returns minutes until the next anxiety check-in.
    Falls back to 5 minutes when there is insufficient history.
    average_scroll_speed is compared against 1 (normal speed).
    """
    if len(anxiety_list) < 4:
        return 5.0

    arr = np.array(anxiety_list)
    avg = np.mean(arr)
    std = np.std(arr)
    return float(avg + std - math.fabs(1 - average_scroll_speed))


def warn_high_anxiety(anxiety_list: list) -> bool:
    """True when the latest score is 8 or above."""
    if not anxiety_list:
        return False
    return anxiety_list[-1] >= 8


def warn_high_change(anxiety_list: list, time_between: float = 1, threshold: float = 3) -> bool:
    """True when the rate of change between the last two readings exceeds the threshold."""
    if len(anxiety_list) < 2:
        return False
    return math.fabs(anxiety_list[-1] - anxiety_list[-2]) / time_between >= threshold


def warn_slow_scroll_speed(average_scroll_speed: float, threshold: float = 0.5) -> bool:
    """True when average scroll speed is at or below the threshold."""
    return average_scroll_speed <= threshold


def build_anxiety_plot(anxiety_list: list, check_in_intervals: list) -> str:
    """
    Renders the anxiety-over-time chart and returns it as a base64 PNG
    so it can be embedded directly in a JSON response.
    """
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(np.cumsum(check_in_intervals), anxiety_list, marker='o', linewidth=2)
    ax.set_xlabel('Time (minutes)')
    ax.set_ylabel('Anxiety Level')
    ax.set_title('Anxiety Levels Over Time')
    ax.set_ylim(0, 11)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


# ---------------------------------------------------------------------------
# Sefaria helpers
# ---------------------------------------------------------------------------

def flatten_text(data):
    if isinstance(data, str):
        return [data]
    if isinstance(data, list):
        result = []
        for item in data:
            result.extend(flatten_text(item))
        return sorted(result)
    return []


def get_sefaria_text(ref: str):
    encoded_ref = urllib.parse.quote(ref)
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}?context=0"
    try:
        r = requests.get(url, timeout=5).json()
        if "versions" in r:
            for v in r['versions']:
                if v.get('language') == 'he' and v.get('text'):
                    return flatten_text(v['text'])
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_prayer", methods=["POST"])
def get_prayer():
    path = request.json.get('path', [])
    book = path[0].replace('_', ' ')
    segments = ", ".join(path[1:])
    full_ref = f"{book}, {segments}"

    # Reset scroll history for a fresh start on a new prayer
    speed_history.clear()

    txt = get_sefaria_text(full_ref)

    # Basic link hunter / fallback
    if not txt:
        try:
            links = requests.get(
                f"https://www.sefaria.org/api/links/{urllib.parse.quote(full_ref)}"
            ).json()
            if isinstance(links, list) and links:
                txt = get_sefaria_text(links[0].get('ref'))
        except Exception:
            pass

    return jsonify({"text": txt or "Liturgy not found.", "error": not txt})


@app.route("/stream_sample", methods=["POST"])
def stream_sample():
    """
    Receives a scroll-activity sample and evaluates both flatline (scroll) and
    anxiety-based warnings using the current scroll speed average.
    """
    is_active = request.json.get('active', 0)
    speed_history.append(is_active)

    # --- Scroll flatline alert (unchanged) ---
    flatline = False
    if len(speed_history) >= 3:
        if all(v == 0 for v in list(speed_history)[-3:]):
            flatline = True

    # --- Derive average scroll speed for anxiety helpers ---
    average_scroll_speed = float(np.mean(list(speed_history))) if speed_history else 0.0

    # --- Anxiety warnings (only meaningful once we have check-in data) ---
    slow_scroll = warn_slow_scroll_speed(average_scroll_speed)
    high_anxiety = warn_high_anxiety(anxiety_list)
    high_change = warn_high_change(anxiety_list)

    # How long until the next check-in is suggested (minutes)
    next_check_in = calculate_next_anxiety_check(anxiety_list, average_scroll_speed)

    return jsonify({
        "flatline_alert": flatline,
        "slow_scroll_alert": slow_scroll,
        "high_anxiety_alert": high_anxiety,
        "high_change_alert": high_change,
        "next_checkin_minutes": next_check_in,
        "average_scroll_speed": average_scroll_speed,
    })


@app.route("/submit_checkin", methods=["POST"])
def submit_checkin():
    """
    Accepts a check-in payload, validates the anxiety score (1–10),
    appends it to the session history, and returns warning flags plus
    an updated chart image.
    """
    data = request.json or {}

    # Validate anxiety score
    try:
        score = int(data.get("anxiety_score", 0))
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "anxiety_score must be an integer."}), 400

    if not (1 <= score <= 10):
        return jsonify({
            "status": "error",
            "message": "anxiety_score must be between 1 and 10."
        }), 400

    # Record how many minutes elapsed since the last check-in
    interval = float(data.get("interval_minutes", 5))
    anxiety_list.append(score)
    check_in_intervals.append(interval)
    checkin_history.append(data)

    print(f"Check-in received: {data}")

    # Derive current scroll speed from history
    average_scroll_speed = float(np.mean(list(speed_history))) if speed_history else 0.0

    # Build response with warning flags
    response = {
        "status": "ok",
        "high_anxiety_alert": warn_high_anxiety(anxiety_list),
        "high_change_alert": warn_high_change(anxiety_list),
        "slow_scroll_alert": warn_slow_scroll_speed(average_scroll_speed),
        "next_checkin_minutes": calculate_next_anxiety_check(anxiety_list, average_scroll_speed),
    }

    # Attach a chart once we have enough data points
    if len(anxiety_list) >= 2:
        response["chart_png_base64"] = build_anxiety_plot(anxiety_list, check_in_intervals)

    return jsonify(response)


@app.route("/anxiety_chart", methods=["GET"])
def anxiety_chart():
    """Standalone endpoint that returns the latest anxiety chart as a PNG image."""
    if len(anxiety_list) < 2:
        return jsonify({"error": "Not enough data to plot yet."}), 400

    png_b64 = build_anxiety_plot(anxiety_list, check_in_intervals)
    img_bytes = base64.b64decode(png_b64)
    from flask import Response
    return Response(img_bytes, mimetype='image/png')


if __name__ == "__main__":
    app.run(debug=True, port=5001)
