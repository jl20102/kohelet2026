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
    setupNudgeUI();
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

                <div style="display: flex; justify-content: center; gap: 15px; margin-top: 20px;">
                    <button onclick="dismissNudge()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #888; color: white; border: none; border-radius: 5px;">Cancel</button>
                    <button onclick="submitCheckIn()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px;">Check In</button>
                </div>
            </div>
        `;
    }
}

function showMinyanCheck() {
    document.getElementById('nudge-overlay').innerHTML = `
        <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
            <h3>Continuing Prayer</h3>
            <p>Where is the Minyan holding?</p>
            <p style="margin-top: 10px;">If necessary to catch up, skip everything except:</p>
            <ul style="list-style: none; padding: 0; margin: 15px 0; font-weight: bold; font-size: 1.1rem; line-height: 1.5;">
                <li>בָּרוּךְ שֶׁאָמַר</li>
                <li>אַשְׁרֵי</li>
                <li>יִשְׁתַּבַּח</li>
                <li>שְׁמַע</li>
                <li>עֲמִידָה</li>
            </ul>
            <button onclick="dismissNudge()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px;">Return to Prayer</button>
        </div>
    `;
}

function showMuscleRelaxation() {
    const text = '<p style="margin-bottom:15px">Let’s release some tension from your body.<br>Starting at your toes, gently tense the muscles for a few seconds, then relax them.<br>Slowly move upward–feet, calves, legs, and so on–until you reach your head.<br>Take your time with each step.</p>';
    document.getElementById('nudge-overlay').innerHTML = `
        <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
            <h3>Guidance</h3>
            ${text}
            <p style="margin-top:15px; font-weight:bold;">Did this help?</p>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 20px;">
                <button onclick="showVisualization()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #888; color: white; border: none; border-radius: 5px;">No</button>
                <button onclick="showMinyanCheck()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px;">Yes</button>
            </div>
        </div>
    `;
}

function showVisualization() {
    const text = '<p style="margin-bottom:15px">Close your eyes if you feel comfortable.<br>Imagine a calm, peaceful place–maybe a beach, a forest, or somewhere you love.<br>Notice what you see, hear, and feel.<br>Stay there for a few moments and let yourself relax into it.</p>';
    document.getElementById('nudge-overlay').innerHTML = `
        <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
            <h3>Guidance</h3>
            ${text}
            <p style="margin-top:15px; font-weight:bold;">Did this help?</p>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 20px;">
                <button onclick="showMindfulness()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #888; color: white; border: none; border-radius: 5px;">No</button>
                <button onclick="showMinyanCheck()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px;">Yes</button>
            </div>
        </div>
    `;
}

function showMindfulness() {
    const text = '<p style="margin-bottom:15px">Gently close your eyes.<br>Bring your attention to your breath—nothing else.<br>If your mind wanders, that’s okay—just return to your breathing.<br>Stay here for as long as you need.</p>';
    document.getElementById('nudge-overlay').innerHTML = `
        <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
            <h3>Guidance</h3>
            ${text}
            <p style="margin-top:15px; font-weight:bold;">Did this help?</p>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 20px;">
                <button onclick="showGrounding()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #888; color: white; border: none; border-radius: 5px;">No</button>
                <button onclick="showMinyanCheck()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px;">Yes</button>
            </div>
        </div>
    `;
}

function showGrounding() {
    const text = '<p style="margin-bottom:15px">Let’s reconnect with the present moment.<br>Take a slow breath, and notice:<br>5 things you can see<br>4 things you can touch<br>3 things you can hear<br>2 things you can smell<br>1 thing you can taste<br>Move through this slowly and gently.</p>';
    document.getElementById('nudge-overlay').innerHTML = `
        <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
            <h3>Guidance</h3>
            ${text}
            <p style="margin-top:15px; font-weight:bold;">Did this help?</p>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 20px;">
                <button onclick="showPhysicalReset()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #888; color: white; border: none; border-radius: 5px;">No</button>
                <button onclick="showMinyanCheck()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px;">Yes</button>
            </div>
        </div>
    `;
}

function showPhysicalReset() {
    const text = '<p style="margin-bottom:15px">If you’re still feeling overwhelmed, it’s okay to pause.<br>Stand up, stretch, or take a short walk.<br>Roll your shoulders, loosen your back, and give your body a moment to reset.<br>You can return whenever you’re ready.</p>';
    document.getElementById('nudge-overlay').innerHTML = `
        <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
            <h3>Guidance</h3>
            ${text}
            <p style="margin-top:15px; font-weight:bold;">Did this help?</p>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 20px;">
                <button onclick="showSeekHelp()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #888; color: white; border: none; border-radius: 5px;">No</button>
                <button onclick="showMinyanCheck()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px;">Yes</button>
            </div>
        </div>
    `;
}

function showSeekHelp() {
    document.getElementById('nudge-overlay').innerHTML = `
        <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
            <h3>Please Seek Help</h3>
            <p>It seems like you are having a tough time. Please speak to an adult or another person for help.</p>
            <button onclick="dismissNudge()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #888; color: white; border: none; border-radius: 5px; margin-top: 15px;">Close</button>
        </div>
    `;
}

async function submitCheckIn() {
    const anxiety = parseInt(document.getElementById('anx-slider').value);
    const focus = parseInt(document.getElementById('foc-slider').value);
    
    // Send data in background
    fetch('/submit_checkin', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ anxiety, focus })
    });

    let advice = "";
    if (anxiety >= 7) advice += '<p style="margin-bottom:15px">Let’s slow things down together.<br>Place one hand on your stomach and one on your chest.<br>Breathe in slowly through your nose, letting your stomach rise more than your chest.<br>Then gently exhale through your mouth.<br>Repeat at your own pace.</p>';
    if (focus <= 4) advice += '<p>You seem to be losing focus. It might be a good idea to take a short break.</p>';

    if (advice) {
        document.getElementById('nudge-overlay').innerHTML = `
            <div style="background: white; padding: 25px; border-radius: 10px; text-align: center; max-width: 90%; color: #333;">
                <h3>Guidance</h3>
                ${advice}
                <p style="margin-top:15px; font-weight:bold;">Did this help?</p>
                <div style="display: flex; justify-content: center; gap: 15px; margin-top: 20px;">
                    <button onclick="showMuscleRelaxation()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #888; color: white; border: none; border-radius: 5px;">No</button>
                    <button onclick="showMinyanCheck()" style="padding: 10px 20px; font-size: 1rem; cursor: pointer; background-color: #28a745; color: white; border: none; border-radius: 5px;">Yes</button>
                </div>
            </div>
        `;
    } else {
        dismissNudge();
    }
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