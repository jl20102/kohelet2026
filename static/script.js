let allItems = [];
let pos = -1;
let menuChain = [];
let lastScrollTop = 0;
let lastTimestamp = Date.now();
let speedDataPoints = new Array(50).fill(0); // For the graph

const scrollBox = document.getElementById('scroll-box');
const canvas = document.getElementById('heartbeat-canvas');
const ctx = canvas.getContext('2d');

// --- Initialization & Menu Logic ---
async function init() {
    const res = await fetch(`https://www.sefaria.org/api/v2/index/${document.getElementById('nusach').value}`);
    const data = await res.json();
    document.getElementById('dynamic-menus').innerHTML = '';
    buildMenus(data.schema, []);
}

function buildMenus(node, currentChain) {
    if (!node.nodes) return;
    const s = document.createElement('select');
    s.options.add(new Option("-- Select --", ""));
    node.nodes.forEach((n, i) => s.options.add(new Option(n.enTitle || n.key, JSON.stringify({i, n}))));
    s.onchange = () => {
        while (s.nextSibling) s.parentElement.removeChild(s.nextSibling);
        const sel = JSON.parse(s.value);
        if (sel.n.nodes) buildMenus(sel.n, [...currentChain, sel.n.enTitle || sel.n.key]);
        else { document.getElementById('open-btn').disabled = false; allItems = node.nodes; pos = sel.i; menuChain = currentChain; }
    };
    document.getElementById('dynamic-menus').appendChild(s);
}

// --- Scrolling & Visualization ---
scrollBox.addEventListener('scroll', async () => {
    const now = Date.now();
    const dt = (now - lastTimestamp) / 1000;
    const dy = Math.abs(scrollBox.scrollTop - lastScrollTop);
    
    if (dt > 0.1) {
        const speed = Math.round(dy / dt);
        updateGraph(speed);
        
        try {
            const res = await fetch('/stream_speed', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ speed })
            });
            const data = await res.json();
            document.getElementById('avg-val').innerText = data.avg_speed;
            if (data.low_speed_alert) document.getElementById('nudge-overlay').style.display = 'flex';
        } catch (e) {}

        lastScrollTop = scrollBox.scrollTop;
        lastTimestamp = now;
    }
});

function updateGraph(newSpeed) {
    speedDataPoints.push(newSpeed);
    speedDataPoints.shift();
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.strokeStyle = '#8DA399';
    ctx.lineWidth = 2;
    
    const step = canvas.width / (speedDataPoints.length - 1);
    for (let i = 0; i < speedDataPoints.length; i++) {
        // Map speed to Y axis (0 to 200px/s)
        const y = canvas.height - (Math.min(speedDataPoints[i], 200) / 200 * canvas.height);
        if (i === 0) ctx.moveTo(0, y);
        else ctx.lineTo(i * step, y);
    }
    ctx.stroke();
}

function dismissNudge() {
    document.getElementById('nudge-overlay').style.display = 'none';
    lastTimestamp = Date.now(); // Reset timer
}

// --- Text Fetching ---
async function fetchText() {
    const path = [document.getElementById('nusach').value, ...menuChain, allItems[pos].enTitle || allItems[pos].key];
    const res = await fetch('/get_prayer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path})
    });
    const data = await res.json();
    document.getElementById('display').innerHTML = data.text;
    document.getElementById('prev').disabled = pos <= 0;
    document.getElementById('next').disabled = pos >= allItems.length - 1;
}

async function loadFirst() { await fetchText(); }
async function move(dir) { pos += dir; await fetchText(); }

window.onload = init;