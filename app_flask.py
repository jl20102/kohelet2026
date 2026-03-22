from flask import Flask, render_template_string, request, jsonify
import requests
import urllib.parse

app = Flask(__name__)

BASE_URL = "https://www.sefaria.org/api"
INDEX_NAME = "Siddur_Ashkenaz"

# --- HTML/CSS/JS COMBINED ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tefilot - Siddur Browser</title>
    <style>
        body {
            margin: 0; padding: 0; display: flex; min-height: 100vh;
            background: linear-gradient(135deg, #e0d7c6 0%, #a3c1ad 50%, #7da2a9 100%);
            font-family: 'Georgia', serif;
        }
        /* Sidebar Navigation */
        .sidebar {
            width: 300px; background: rgba(255, 255, 255, 0.6);
            padding: 20px; border-right: 1px solid rgba(0,0,0,0.1);
            display: flex; flex-direction: column; gap: 15px;
        }
        .sidebar h2 { color: #4a6670; font-size: 1.2rem; text-transform: uppercase; }
        select { padding: 10px; border-radius: 5px; border: 1px solid #c5b358; width: 100%; background: white; }
        
        /* Main Content Container */
        .main-content { flex: 1; display: flex; justify-content: center; align-items: flex-start; padding: 40px; }
        .container {
            width: 100%; max-width: 700px; background: rgba(255, 255, 255, 0.88);
            padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border: 2px solid #c5b358; text-align: center; position: relative;
        }
        h1 { color: #4a6670; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px; }
        
        .prayer-space { 
            color: #333; line-height: 1.8; font-size: 1.6rem; min-height: 200px; padding: 20px;
            direction: rtl; text-align: right; white-space: pre-wrap; border-top: 1px solid #eee;
        }
        .footer-tag { margin-top: 30px; background: #7da2a9; color: white; display: inline-block; padding: 5px 25px; border-radius: 20px; font-size: 0.9rem; }
        button { background: #7da2a9; color: white; border: none; padding: 12px 25px; border-radius: 20px; cursor: pointer; width: 100%; font-size: 1rem; margin-top: 10px; }
        button:hover { background: #4a6670; }
    </style>
</head>
<body>

    <div class="sidebar">
        <h2>Siddur Navigator</h2>
        <label>Section</label>
        <select id="level1" onchange="updateLevel2()"><option>Loading...</option></select>
        
        <label>Service</label>
        <select id="level2" onchange="updateLevel3()"><option value="">-- Select --</option></select>
        
        <label>Prayer</label>
        <select id="level3"><option value="">-- Select --</option></select>
        
        <form action="/" method="POST" id="prayerForm">
            <input type="hidden" name="ref_string" id="ref_string">
            <button type="button" onclick="submitPrayer()">Display Prayer</button>
        </form>
    </div>

    <div class="main-content">
        <div class="container">
            <h1>Tefilot</h1>
            <div class="prayer-space" id="prayerContent">
                {% if prayer_text %}
                    {{ prayer_text }}
                {% else %}
                    <p style="color: #888; font-style: italic; direction: ltr; text-align: center;">
                        Select a prayer from the sidebar to begin...
                    </p>
                {% endif %}
            </div>
            <div class="footer-tag">Reflections</div>
        </div>
    </div>

    <script>
        let fullIndex = {};

        // 1. Fetch the Index when page loads
        fetch('/get_index')
            .then(response => response.json())
            .then(data => {
                fullIndex = data;
                const l1 = document.getElementById('level1');
                l1.innerHTML = '<option value="">-- Select --</option>';
                fullIndex.nodes.forEach(node => {
                    let opt = document.createElement('option');
                    opt.value = node.enTitle || node.key;
                    opt.innerHTML = node.enTitle || node.key;
                    l1.appendChild(opt);
                });
            });

        function updateLevel2() {
            const val1 = document.getElementById('level1').value;
            const l2 = document.getElementById('level2');
            const l3 = document.getElementById('level3');
            l2.innerHTML = '<option value="">-- Select --</option>';
            l3.innerHTML = '<option value="">-- Select --</option>';

            const node1 = fullIndex.nodes.find(n => (n.enTitle || n.key) === val1);
            if (node1 && node1.nodes) {
                node1.nodes.forEach(node => {
                    let opt = document.createElement('option');
                    opt.value = node.enTitle || node.key;
                    opt.innerHTML = node.enTitle || node.key;
                    l2.appendChild(opt);
                });
            }
        }

        function updateLevel3() {
            const val1 = document.getElementById('level1').value;
            const val2 = document.getElementById('level2').value;
            const l3 = document.getElementById('level3');
            l3.innerHTML = '<option value="">-- Select --</option>';

            const node1 = fullIndex.nodes.find(n => (n.enTitle || n.key) === val1);
            const node2 = node1.nodes.find(n => (n.enTitle || n.key) === val2);
            
            if (node2 && node2.nodes) {
                node2.nodes.forEach(node => {
                    let opt = document.createElement('option');
                    opt.value = node.enTitle || node.key;
                    opt.innerHTML = node.enTitle || node.key;
                    l3.appendChild(opt);
                });
            }
        }

        function submitPrayer() {
            const v1 = document.getElementById('level1').value;
            const v2 = document.getElementById('level2').value;
            const v3 = document.getElementById('level3').value;
            
            // Build the comma-separated Ref string
            let path = [v1];
            if(v2) path.push(v2);
            if(v3) path.push(v3);
            
            document.getElementById('ref_string').value = path.join(', ');
            document.getElementById('prayerForm').submit();
        }
    </script>
</body>
</html>
"""

def flatten_text(text_data):
    if isinstance(text_data, list):
        return "\n\n".join([flatten_text(item) for item in text_data])
    return str(text_data)

@app.route("/get_index")
def get_index():
    # Helper for the JavaScript to get the structure
    res = requests.get(f"{BASE_URL}/v2/index/{INDEX_NAME}")
    return jsonify(res.json()['schema'])

@app.route("/", methods=["GET", "POST"])
def home():
    prayer_text = None
    if request.method == "POST":
        raw_ref = request.form.get("ref_string", "")
        # Construct Sefaria URL
        parts = [p.strip().replace(" ", "_") for p in raw_ref.split(",")]
        full_path = [INDEX_NAME] + parts
        ref_string = ",_".join(full_path)
        
        encoded_ref = urllib.parse.quote(ref_string).replace("%2C", ",")
        url = f"{BASE_URL}/v3/texts/{encoded_ref}?context=0"
        
        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                for v in data.get('versions', []):
                    if v.get('language') == 'he':
                        prayer_text = flatten_text(v.get('text', []))
                        break
        except:
            prayer_text = "Error loading prayer."

    return render_template_string(HTML_TEMPLATE, prayer_text=prayer_text)

if __name__ == "__main__":
    app.run(debug=True, port=5000)