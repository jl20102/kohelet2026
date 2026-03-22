let allItems = [];
let pos = -1;
let menuChain = [];
let scrollSpeeds = [];
let lastScrollTop = 0;
let lastTimestamp = Date.now();
let idleTimer = null;
const IDLE_LIMIT = 5000; // 5 Seconds

const scrollBox = document.getElementById('scroll-box');
const nudge = document.getElementById('nudge-overlay');

// 1. Initialize Menu
async function init() {
    const nusach = document.getElementById('nusach').value;
    const res = await fetch(`https://www.sefaria.org/api/v2/index/${nusach}`);
    const data = await res.json();
    document.getElementById('dynamic-menus').innerHTML = '';
    buildMenus(data.schema, []);
}

// 2. Build Menus
function buildMenus(node, currentChain) {
    if (!node.nodes) return;
    const s = document.createElement('select');
    s.options.add(new Option("-- Select --", ""));
    node.nodes.forEach((n, i) => s.options.add(new Option(n.enTitle || n.key, JSON.stringify({i, n}))));
    
    s.onchange = () => {
        while (s.nextSibling) s.parentElement.removeChild(s.nextSibling);
        if (!s.value) return;
        const selected = JSON.parse(s.value);
        if (selected.n.nodes) {
            buildMenus(selected.n, [...currentChain, selected.n.enTitle || selected.n.key]);
        } else {
            document.getElementById('open-btn').disabled = false;
            allItems = node.nodes;
            pos = selected.i;
            menuChain = currentChain;
        }
    };
    document.getElementById('dynamic-menus').appendChild(s);
}

// 3. Scroll & Speed Tracking
scrollBox.addEventListener('scroll', () => {
    const now = Date.now();
    const dt = (now - lastTimestamp) / 1000;
    const dy = Math.abs(scrollBox.scrollTop - lastScrollTop);
    
    if (dt > 0.1) {
        const speed = Math.round(dy / dt);
        document.getElementById('speed-val').innerText = speed;
        scrollSpeeds.push({s: speed, t: now});
        
        resetIdleTimer();
        lastScrollTop = scrollBox.scrollTop;
        lastTimestamp = now;
    }
});

function resetIdleTimer() {
    clearTimeout(idleTimer);
    document.getElementById('idle-status').innerText = "Active";
    nudge.style.display = 'none';
    idleTimer = setTimeout(triggerNudge, IDLE_LIMIT);
}

function triggerNudge() {
    document.getElementById('idle-status').innerText = "IDLE";
    nudge.style.display = 'flex';
    // Log to backend
    fetch('/log_activity', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: 'idle', avg_speed: 0})
    });
}

function dismissNudge() {
    resetIdleTimer();
}

// 4. Fetching Text
async function loadFirst() { await fetchText(); resetIdleTimer(); }
async function move(dir) { pos += dir; await fetchText(); resetIdleTimer(); }

async function fetchText() {
    const path = [document.getElementById('nusach').value, ...menuChain, allItems[pos].enTitle || allItems[pos].key];
    const res = await fetch('/get_prayer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path})
    });
    const data = await res.json();
    document.getElementById('display').innerHTML = data.text || data.error;
    document.getElementById('prev').disabled = pos <= 0;
    document.getElementById('next').disabled = pos >= allItems.length - 1;
}

window.onload = init;