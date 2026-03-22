from flask import Flask, render_template, request, jsonify
import requests
import urllib.parse
from collections import deque

app = Flask(__name__)

# Store the last 20 speed readings
speed_history = deque(maxlen=20)
THRESHOLD = 20

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
    full_ref = f"{book}, {', '.join(path[1:])}"
    txt = get_sefaria_text(full_ref)
    return jsonify({"text": txt or "Liturgy not found.", "error": not txt})

@app.route("/stream_speed", methods=["POST"])
def stream_speed():
    speed = request.json.get('speed', 0)
    speed_history.append(speed)
    avg_speed = sum(speed_history) / len(speed_history) if speed_history else 0
    
    # Alert if history is full and average drops below threshold
    alert = len(speed_history) == speed_history.maxlen and avg_speed < THRESHOLD
    return jsonify({
        "avg_speed": round(avg_speed, 2),
        "low_speed_alert": alert
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)