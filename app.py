from flask import Flask, render_template, request, jsonify
import requests
import urllib.parse
import re
from collections import deque

app = Flask(__name__)

# speed_history stores 1 for active, 0 for idle (2-second intervals)
speed_history = deque(maxlen=10)
checkin_history = deque(maxlen=50)

def flatten_text(data):
    if isinstance(data, str): return [data]
    if isinstance(data, list):
        result = []
        for item in data: result.extend(flatten_text(item))
        return result
    return []

def get_sefaria_text(ref):
    encoded_ref = urllib.parse.quote(ref)
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}?context=0"
    try:
        r = requests.get(url, timeout=5).json()
        if "versions" in r:
            for v in r['versions']:
                if v.get('language') == 'he' and v.get('text'):
                    return "<br><br>".join(flatten_text(v['text']))
    except: pass
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_prayer", methods=["POST"])
def get_prayer():
    path = request.json.get('path', [])
    book = path[0].replace('_', ' ')
    segments = ", ".join(path[1:])
    full_ref = f"{book}, {segments}"
    
    # Reset history for a fresh start on a new prayer
    speed_history.clear()
    
    txt = get_sefaria_text(full_ref)
    
    # Basic Link Hunter / Fallback
    if not txt:
        try:
            links = requests.get(f"https://www.sefaria.org/api/links/{urllib.parse.quote(full_ref)}").json()
            if isinstance(links, list) and len(links) > 0:
                txt = get_sefaria_text(links[0].get('ref'))
        except: pass

    return jsonify({"text": txt or "Liturgy not found.", "error": not txt})

@app.route("/stream_sample", methods=["POST"])
def stream_sample():
    is_active = request.json.get('active', 0)
    speed_history.append(is_active)
    
    # Alert if last 3 samples (6 seconds) are all 0
    flatline = False
    if len(speed_history) >= 3:
        last_three = list(speed_history)[-3:]
        if all(v == 0 for v in last_three):
            flatline = True
            
    return jsonify({"flatline_alert": flatline})

@app.route("/submit_checkin", methods=["POST"])
def submit_checkin():
    data = request.json
    # Log the user's anxiety and focus levels
    checkin_history.append(data)
    print(f"Check-in received: {data}")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5001)