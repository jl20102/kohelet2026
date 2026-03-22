from flask import Flask, render_template_string, request, jsonify
import requests, urllib.parse, re

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Siddur - Pure Focus</title>
    <style>
        :root { --sage: #8DA399; --cream: #FFFFE0; --text: #2C3330; }
        
        body { 
            margin: 0; padding: 0; 
            background-color: var(--cream); 
            font-family: 'Georgia', serif; 
            color: var(--text);
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

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
            background: #fff; font-size: 1rem; min-width: 150px;
        }

        .breadcrumb {
            font-size: 0.85rem;
            color: #666;
            background: #f9f9f9;
            padding: 5px 15px;
            border-radius: 20px;
            border: 1px solid #eee;
            max-width: 90%;
            text-align: center;
        }

        .nav-row { display: flex; gap: 15px; align-items: center; margin-top: 10px; }

        .btn {
            padding: 12px 30px;
            font-size: 1rem;
            font-weight: bold;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            transition: 0.3s;
        }
        .btn-main { background-color: var(--sage); color: white; }
        .btn-main:disabled { background-color: #ccc; cursor: not-allowed; opacity: 0.6; }
        .btn-step { background-color: white; border: 2px solid var(--sage); color: var(--sage); }
        .btn-step:disabled { border-color: #ddd; color: #aaa; cursor: not-allowed; }
        
        .btn-print { 
            background-color: #f0f0f0; 
            color: #555; 
            font-size: 0.8rem; 
            padding: 8px 20px;
            border: 1px solid #ccc;
        }

        .prayer-container {
            flex: 1;
            overflow-y: auto;
            padding: 40px 20px;
            text-align: center;
        }

        .hebrew-text {
            direction: rtl;
            font-size: 2.8rem;
            line-height: 2.2;
            max-width: 900px;
            margin: 0 auto;
            white-space: pre-wrap;
        }

        .loading-text { color: var(--sage); font-style: italic; display: none; margin-bottom: 10px; }
        .error-text { color: #d9534f; font-weight: bold; margin-top: 10px; max-width: 600px; }

        @media print {
            .header-controls { display: none; }
            .prayer-container { padding: 0; }
            .hebrew-text { font-size: 20pt; line-height: 1.6; color: black; }
        }
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

        <div id="breadcrumb-display" class="breadcrumb">Select a path...</div>

        <div class="nav-row">
            <button class="btn btn-step" id="prev" onclick="move(-1)" disabled>← BACK</button>
            <button class="btn btn-main" id="open-btn" onclick="loadFirst()" disabled>OPEN PRAYER</button>
            <button class="btn btn-step" id="next" onclick="move(1)" disabled>NEXT PRAYER →</button>
        </div>
        
        <div style="display: flex; gap: 10px; align-items: center;">
            <div id="status-label" style="font-size: 0.8rem; font-weight: bold; color: var(--sage);">READY</div>
            <button class="btn btn-print" id="print-btn" onclick="printPrayer()" style="display:none;">PRINT PAGE</button>
        </div>
    </div>

    <div class="prayer-container" id="scroll-box">
        <div id="loading" class="loading-text">Finding the words...</div>
        <div id="display" class="hebrew-text">Please complete your selection to begin.</div>
        <div id="error" class="error-text" style="display:none;"></div>
    </div>

    <script>
        let allItems = [];
        let pos = -1;
        let menuChain = []; 

        async function init() {
            const nusach = document.getElementById('nusach').value;
            try {
                const res = await fetch(`https://www.sefaria.org/api/v2/index/${nusach}`);
                const data = await res.json();
                document.getElementById('dynamic-menus').innerHTML = '';
                document.getElementById('open-btn').disabled = true;
                document.getElementById('print-btn').style.display = 'none';
                updateBreadcrumb([]);
                allItems = [];
                pos = -1;
                menuChain = [];
                buildMenus(data.schema, []);
            } catch (e) {
                console.error("Initialization failed", e);
            }
        }

        function updateBreadcrumb(chain, leafTitle = "") {
            const nusachElem = document.getElementById('nusach');
            const nusachText = nusachElem.options[nusachElem.selectedIndex].text;
            let parts = [nusachText, ...chain];
            if (leafTitle) parts.push(leafTitle);
            document.getElementById('breadcrumb-display').innerText = parts.join(" › ");
        }

        function buildMenus(node, currentChain) {
            if (!node.nodes || node.nodes.length === 0) return;

            const s = document.createElement('select');
            s.options.add(new Option("-- Select --", ""));
            
            node.nodes.forEach((n, i) => {
                const title = n.enTitle || n.key || `Section ${i+1}`;
                s.options.add(new Option(title, JSON.stringify({index: i, node: n})));
            });
            
            s.onchange = () => {
                let next = s.nextSibling;
                while (next) {
                    let toRemove = next;
                    next = next.nextSibling;
                    toRemove.parentElement.removeChild(toRemove);
                }
                
                if (s.value === "") {
                    document.getElementById('open-btn').disabled = true;
                    updateBreadcrumb(currentChain);
                    return;
                }

                const selected = JSON.parse(s.value);
                const selectedNode = selected.node;
                const selectedTitle = selectedNode.enTitle || selectedNode.key;

                if (selectedNode.nodes && selectedNode.nodes.length > 0) {
                    document.getElementById('open-btn').disabled = true;
                    const newChain = [...currentChain, selectedTitle];
                    updateBreadcrumb(newChain);
                    buildMenus(selectedNode, newChain);
                } else {
                    document.getElementById('open-btn').disabled = false;
                    allItems = node.nodes; 
                    pos = selected.index;
                    menuChain = currentChain;
                    updateBreadcrumb(currentChain, selectedTitle);
                }
            };
            document.getElementById('dynamic-menus').appendChild(s);
        }

        function printPrayer() {
            const content = document.getElementById('display').innerHTML;
            const title = document.getElementById('breadcrumb-display').innerText;
            const printWindow = window.open('', '', 'height=600,width=800');
            printWindow.document.write('<html><head><title>Siddur Print</title>');
            printWindow.document.write('<style>body{font-family:serif;text-align:center;direction:rtl;padding:40px;} .title{font-size:14pt;color:#666;margin-bottom:30px;direction:ltr;} .content{font-size:24pt;line-height:1.8;}</style>');
            printWindow.document.write('</head><body>');
            printWindow.document.write('<div class="title">' + title + '</div>');
            printWindow.document.write('<div class="content">' + content + '</div>');
            printWindow.document.write('</body></html>');
            printWindow.document.close();
            printWindow.print();
        }

        async function loadFirst() { await fetchText(); }
        async function move(dir) { if (allItems.length > 0) { pos += dir; await fetchText(); } }

        async function fetchText() {
            let pathParts = [document.getElementById('nusach').value, ...menuChain];
            if (pos >= 0 && pos < allItems.length) {
                pathParts.push(allItems[pos].enTitle || allItems[pos].key);
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('display').innerHTML = "";
            
            try {
                const res = await fetch('/get_prayer', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: pathParts})
                });
                const data = await res.json();
                
                if (data.error) {
                    document.getElementById('error').innerText = data.error;
                    document.getElementById('error').style.display = 'block';
                    document.getElementById('print-btn').style.display = 'none';
                } else {
                    document.getElementById('display').innerHTML = data.text;
                    document.getElementById('print-btn').style.display = 'inline-block';
                    updateBreadcrumb(menuChain, allItems[pos].enTitle || allItems[pos].key);
                }
            } catch (e) {
                document.getElementById('error').innerText = "Network Error: Could not reach server.";
                document.getElementById('error').style.display = 'block';
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('scroll-box').scrollTop = 0;
                document.getElementById('prev').disabled = (pos <= 0);
                document.getElementById('next').disabled = (pos >= allItems.length - 1);
                document.getElementById('status-label').innerText = `STEP ${pos + 1} OF ${allItems.length}`;
            }
        }

        window.onload = init;
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

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
    r = get_sefaria_json(f"https://www.sefaria.org/api/texts/{encoded_ref}?context=0")
    if r and r.get("he"):
        return "<br><br>".join(flatten_text(r["he"]))
    r3 = get_sefaria_json(f"https://www.sefaria.org/api/v3/texts/{encoded_ref}?context=0")
    if r3 and r3.get("versions"):
        for v in r3['versions']:
            if v.get('language') == 'he' and v.get('text'):
                return "<br><br>".join(flatten_text(v['text']))
    return None

@app.route("/get_prayer", methods=["POST"])
def get_prayer():
    path = request.json.get('path', [])
    if not path: return jsonify({"error": "No path selected"})
    
    book = path[0].replace('_', ' ')
    segments = ", ".join(path[1:])
    full_ref = f"{book}, {segments}"
    
    try:
        # Step 1: Direct lookup
        txt = get_sefaria_text(full_ref)
        
        # Step 2: Tanakh Fallback (e.g. "Psalm 100")
        if not txt:
            # Regex to catch "Psalm X" or "Exodus X"
            match = re.search(r"(Psalm|Exodus|Numbers|Deuteronomy|Leviticus|Genesis)\s+(\d+)", segments)
            if match:
                book_name = "Psalms" if match.group(1) == "Psalm" else match.group(1)
                chapter = match.group(2)
                txt = get_sefaria_text(f"{book_name} {chapter}")

        # Step 3: Link Hunter
        if not txt:
            links_data = get_sefaria_json(f"https://www.sefaria.org/api/links/{urllib.parse.quote(full_ref)}")
            if isinstance(links_data, list):
                for link in links_data:
                    if not isinstance(link, dict): continue
                    target = link.get('ref', '')
                    if target and target != full_ref:
                        txt = get_sefaria_text(target)
                        if txt: break

        # Step 4: Kaddish Fallback
        if not txt and "Kaddish" in full_ref:
            fallbacks = ["Siddur Ashkenaz, Berachot, Kaddish", "Siddur Sefard, Berachot, Kaddish"]
            for f in fallbacks:
                txt = get_sefaria_text(f)
                if txt: break

        # Step 5: Segment 1 Fallback
        if not txt:
            txt = get_sefaria_text(f"{full_ref} 1")

        if not txt:
            return jsonify({"error": f"The liturgy at '{full_ref}' is unavailable."})

        return jsonify({"text": txt})
    except Exception as e:
        return jsonify({"error": f"Internal Error: {str(e)}"})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5001, debug=True)