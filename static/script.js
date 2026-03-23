let allItems = [];
let pos = -1;
let menuChain = [];

let isPrayerOpen = false;
let userActiveThisInterval = 0;
let lastScrollTop = 0;
let graphData = new Array(40).fill(0);

const scrollBox = document.getElementById('scroll-box');
const canvas = document.getElementById('heartbeat-canvas');
const ctx = canvas.getContext('2d');

// Life-sign listeners
const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
activityEvents.forEach(name => {
    window.addEventListener(name, () => {
        if (isPrayerOpen) userActiveThisInterval = 1; 
    }, {passive: true});
});

// --- UNIFORM SAMPLING (EVERY 2 SECONDS) ---
setInterval(async () => {
    if (!isPrayerOpen) {
        document.getElementById('focus-dot').classList.remove('focus-active');
        return;
    }

    document.getElementById('focus-dot').classList.add('focus-active');

    // Check if scroll position changed manually
    if (scrollBox.scrollTop !== lastScrollTop) {
        userActiveThisInterval = 1;
    }

    // Update Graph Visually (1 for active pulse, 0 for flat)
    updateGraph(userActiveThisInterval);

    try {
        const res = await fetch('/stream_sample', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ active: userActiveThisInterval })
        });
        const data = await res.json();
        
        if (data.flatline_alert) {
            document.getElementById('nudge-overlay').style.display = 'flex';
        }
    } catch (e) { console.error("Sampling error", e); }

    // Reset for next window
    userActiveThisInterval = 0;
    lastScrollTop = scrollBox.scrollTop;
}, 2000);

function updateGraph(val) {
    graphData.push(val);
    graphData.shift();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.strokeStyle = val > 0 ? '#8DA399' : '#eee';
    ctx.lineWidth = 2;
    const step = canvas.width / (graphData.length - 1);
    for (let i = 0; i < graphData.length; i++) {
        const y = graphData[i] > 0 ? 5 : 20; // Pulse up if active
        if (i === 0) ctx.moveTo(0, y);
        else ctx.lineTo(i * step, y);
    }
    ctx.stroke();
}

function dismissNudge() {
    document.getElementById('nudge-overlay').style.display = 'none';
    userActiveThisInterval = 1;
}

function setupNudgeUI() {
    const overlay = document.getElementById('nudge-overlay');
    if (overlay) {
        overlay.innerHTML = `
            <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
                <h3>Check In</h3>
                <p>We noticed you paused. How are you feeling?</p>
                
                <div style="margin: 20px 0;">
                    <label style="font-weight:bold;">Anxiety Level: <span id="anx-val">5</span></label><br>
                    <div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
                        <span style="font-size: 1.5rem;">😌</span>
                        <input type="range" id="anx-slider" min="1" max="10" value="5" oninput="document.getElementById('anx-val').innerText = this.value" style="flex-grow:1">
                        <span style="font-size: 1.5rem;">😰</span>
                    </div>
                </div>

                <div style="margin: 20px 0;">
                    <label style="font-weight:bold;">Focus Level: <span id="foc-val">5</span></label><br>
                    <div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
                        <span style="font-size: 1.5rem;">😵‍💫</span>
                        <input type="range" id="foc-slider" min="1" max="10" value="5" oninput="document.getElementById('foc-val').innerText = this.value" style="flex-grow:1">
                        <span style="font-size: 1.5rem;">🧐</span>
                    </div>
                </div>

                <button onclick="submitCheckIn()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer;">I am here</button>
            </div>
        `;
    }
}

async function submitCheckIn() {
    const anxiety = document.getElementById('anx-slider').value;
    const focus = document.getElementById('foc-slider').value;
    
    // Send data in background
    fetch('/submit_checkin', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ anxiety, focus })
    });
    dismissNudge();
}

// --- Navigation & Data ---
async function init() {
    setupNudgeUI();
    isPrayerOpen = false;
    const res = await fetch(`https://www.sefaria.org/api/v2/index/${document.getElementById('nusach').value}`);
    const data = await res.json();
    document.getElementById('dynamic-menus').innerHTML = '';
    buildMenus(data.schema, []);
}

function buildMenus(node, currentChain) {
    if (!node.nodes) return;
    const s = document.createElement('select');
    s.options.add(new Option("-- Select --", ""));
    node.nodes.forEach((n, i) => s.options.add(new Option(n.heTitle || n.key, JSON.stringify({i, n}))));
    s.onchange = () => {
        while (s.nextSibling) s.parentElement.removeChild(s.nextSibling);
        const sel = JSON.parse(s.value);
        if (sel.n.nodes) buildMenus(sel.n, [...currentChain, sel.n.enTitle || sel.n.key]);
        else { document.getElementById('open-btn').disabled = false; allItems = node.nodes; pos = sel.i; menuChain = currentChain; }
    };
    document.getElementById('dynamic-menus').appendChild(s);
}

async function fetchText() {
    const path = [document.getElementById('nusach').value, ...menuChain, allItems[pos].enTitle || allItems[pos].key];
    const res = await fetch('/get_prayer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path})
    });
    const data = await res.json();
    document.getElementById('display').innerHTML = Array.isArray(data.text) ? data.text.join('<br><br>') : data.text;
    document.getElementById('prev').disabled = pos <= 0;
    document.getElementById('next').disabled = pos >= allItems.length - 1;
    isPrayerOpen = !data.error;
    lastScrollTop = 0;
    scrollBox.scrollTop = 0;
}

async function loadFirst() { await fetchText(); }
async function move(dir) { pos += dir; await fetchText(); }

window.onload = init;