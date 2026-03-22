from flask import Flask, render_template, request, jsonify
import requests
import urllib.parse
import re

app = Flask(__name__)

def flatten_text(data):
    if isinstance(data, str): return [data]
    if isinstance(data, list):
        result = []
        for item in data: result.extend(flatten_text(item))
        return result
    return []

def get_sefaria_json(url):
    try:
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def get_sefaria_text(ref):
    encoded_ref = urllib.parse.quote(ref)
    # Try V1
    r = get_sefaria_json(f"https://www.sefaria.org/api/texts/{encoded_ref}?context=0")
    if r and r.get("he"):
        return "<br><br>".join(flatten_text(r["he"]))
    # Try V3
    r3 = get_sefaria_json(f"https://www.sefaria.org/api/v3/texts/{encoded_ref}?context=0")
    if r3 and r3.get("versions"):
        for v in r3['versions']:
            if v.get('language') == 'he' and v.get('text'):
                return "<br><br>".join(flatten_text(v['text']))
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_prayer", methods=["POST"])
def get_prayer():
    path = request.json.get('path', [])
    if not path: return jsonify({"error": "No path selected"})
    
    book = path[0].replace('_', ' ')
    segments = ", ".join(path[1:])
    full_ref = f"{book}, {segments}"
    
    try:
        txt = get_sefaria_text(full_ref)
        
        # Tanakh Fallback
        if not txt:
            match = re.search(r"(Psalm|Exodus|Numbers|Deuteronomy|Leviticus|Genesis)\s+(\d+)", segments)
            if match:
                book_name = "Psalms" if match.group(1) == "Psalm" else match.group(1)
                txt = get_sefaria_text(f"{book_name} {match.group(2)}")

        # Link Hunter
        if not txt:
            links_data = get_sefaria_json(f"https://www.sefaria.org/api/links/{urllib.parse.quote(full_ref)}")
            if isinstance(links_data, list):
                for link in links_data:
                    if isinstance(link, dict) and link.get('ref') != full_ref:
                        txt = get_sefaria_text(link['ref'])
                        if txt: break

        if not txt:
            txt = get_sefaria_text(f"{full_ref} 1")

        if not txt:
            return jsonify({"error": "Liturgy unavailable. Try the next section."})

        return jsonify({"text": txt})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/log_activity", methods=["POST"])
def log_activity():
    # Placeholder for database logging or analytics
    data = request.json
    print(f"User Status: {data.get('status')} | Speed: {data.get('avg_speed')}px/s")
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, port=5001)