from flask import Flask, render_template_string, request, jsonify
import requests, urllib.parse

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Siddur - Pure Focus</title>
    <style>
        :root { --sage: #8DA399; --cream: #FAFAF7; --text: #2C3330; }
        
        body { 
            margin: 0; padding: 0; 
            background-color: var(--cream); 
            font-family: 'Georgia', serif; 
            color: var(--text);
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        /* TOP CONTROL PANEL - Always visible at the top */
        .header-controls {
            background: white;
            padding: 20px;
            border-bottom: 2px solid var(--sage);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            z-index: 100;
        }

        .selector-row { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
        
        select { 
            padding: 10px; border-radius: 5px; border: 1px solid #ccc; 
            background: var(--cream); font-size: 1rem; min-width: 150px;
        }

        .nav-row { display: flex; gap: 20px; align-items: center; margin-top: 10px; }

        /* THE NAVIGATION BUTTONS */
        .btn {
            padding: 15px 40px;
            font-size: 1.1rem;
            font-weight: bold;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            transition: 0.3s;
        }
        .btn-main { background-color: var(--sage); color: white; }
        .btn-step { background-color: white; border: 2px solid var(--sage); color: var(--sage); }
        .btn:disabled { background-color: #eee; border-color: #ddd; color: #aaa; cursor: not-allowed; }

        /* PRAYER TEXT AREA */
        .prayer-container {
            flex: 1;
            overflow-y: auto;
            padding: 40px 20px;
            text-align: center;
        }

        .hebrew-text {
            direction: rtl;
            font-size: 3rem;
            line-height: 2.2;
            max-width: 900px;
            margin: 0 auto;
            white-space: pre-wrap;
        }

        .loading-text { color: var(--sage); font-style: italic; display: none; margin-bottom: 10px; }
    </style>
</head>
<body>

    <div class="header-controls">
        <div class="selector-row">
            <select id="nusach" onchange="init()">
                <option value="Siddur_Ashkenaz">Ashkenaz</option>
                <option value="Siddur_Sefard">Sefard</option>
                <option value="Siddur_Edot_HaMizrach">Edot HaMizrach</option>
            </select>
            <div id="dynamic-menus" style="display:inline-flex; gap:10px;"></div>
        </div>

        <div class="nav-row">
            <button class="btn btn-step" id="prev" onclick="move(-1)" disabled>BACK</button>
            <button class="btn btn-main" onclick="loadFirst()">OPEN PRAYER</button>
            <button class="btn btn-step" id="next" onclick="move(1)" disabled>NEXT PRAYER</button>
        </div>
        <div id="status-label" style="font-size: 0.8rem; font-weight: bold; color: var(--sage);">READY</div>
    </div>

    <div class="prayer-container" id="scroll-box">
        <div id="loading" class="loading-text">Finding the words...</div>
        <div id="display" class="hebrew-text">Welcome. Select a prayer above to begin.</div>
    </div>

    <script>
        let items = [];
        let pos = -1;

        async function init() {
            const nusach = document.getElementById('nusach').value;
            const res = await fetch(`https://www.sefaria.org/api/v2/index/${nusach}`);
            const data = await res.json();
            document.getElementById('dynamic-menus').innerHTML = '';
            buildMenus(data.schema);
        }

        function buildMenus(node) {
            if (!node.nodes) return;
            const s = document.createElement('select');
            s.options.add(new Option("-- Select Section --", ""));
            node.nodes.forEach((n, i) => s.options.add(new Option(n.enTitle || n.key, i)));
            
            s.onchange = () => {
                while (s.nextSibling) s.parentElement.removeChild(s.nextSibling);
                const nextNode = node.nodes[s.value];
                if (nextNode && nextNode.nodes) {
                    buildMenus(nextNode);
                } else {
                    items = node.nodes;
                    pos = parseInt(s.value);
                }
            };
            document.getElementById('dynamic-menus').appendChild(s);
        }

        async function loadFirst() { if(pos !== -1) await fetchText(); }
        async function move(dir) { pos += dir; await fetchText(); }

        async function fetchText() {
            const selects = document.querySelectorAll('select');
            let path = [];
            selects.forEach(s => {
                if(s.selectedIndex > 0) path.push(s.options[s.selectedIndex].text);
            });
            // Ensure the Nusach ID is at the start of the path for the API
            path[0] = document.getElementById('nusach').value;

            document.getElementById('loading').style.display = 'block';
            
            const res = await fetch('/get_prayer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: path})
            });
            const data = await res.json();
            
            document.getElementById('display').innerHTML = data.text;
            document.getElementById('loading').style.display = 'none';
            document.getElementById('scroll-box').scrollTop = 0;

            // Update UI
            document.getElementById('prev').disabled = (pos <= 0);
            document.getElementById('next').disabled = (pos >= items.length - 1);
            document.getElementById('status-label').innerText = `STEP ${pos + 1} OF ${items.length}`;
        }

        window.onload = init;
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/get_prayer", methods=["POST"])
def get_prayer():
    path = request.json['path']
    ref = ", ".join(path).replace(' ', '_').replace("'", "%27")
    try:
        r = requests.get(f"https://www.sefaria.org/api/v3/texts/{ref}?context=0").json()
        txt = ""
        for v in r.get('versions', []):
            if v.get('language') == 'he' and v.get('text'):
                t = v['text']
                txt = "<br><br>".join(t) if isinstance(t, list) else t
                break
        return jsonify({"text": txt or "Text not found. Try selecting a specific sub-section."})
    except:
        return jsonify({"text": "Error connecting to Sefaria."})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5001)
