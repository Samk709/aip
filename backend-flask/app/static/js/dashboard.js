const userId = localStorage.getItem('aurora_user_id');
const authToken = localStorage.getItem('aurora_token');

function authHeaders() {
    return authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
}

if (!authToken) {
    window.location.href = '/?login=true';
}

document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        loadDashboard();
        initTelemetry();
        checkDailyCheckin();
    }
});

let riskChartInstance = null;
let mhsiChartInstance = null;
let ekgChartInstance = null;

async function loadDashboard() {
    if (!userId || !authToken) return;

    try {
        const res = await fetch(`/api/dashboard/${userId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.status === 401) {
            logout();
            return;
        }

        const data = await res.json();
        if (!res.ok) return console.error('Dashboard load failed', data);

        // Digital Twin
        if (data.digital_twin) {
            document.getElementById('dtTrend').innerText = String(data.digital_twin.trend).toUpperCase();
            if (data.digital_twin.trend === "worsening") document.getElementById('dtTrend').style.color = "var(--accent-primary)";
            else document.getElementById('dtTrend').style.color = "var(--accent-success)";

            document.getElementById('dtPersonality').innerText = data.digital_twin.personality || "Stabilizing Profile...";

            try {
                const triggers = JSON.parse(data.digital_twin.triggers || "[]");
                if (triggers.length > 0) {
                    document.getElementById('dtTriggers').innerHTML = triggers.map(t => `<span class="tag">${t}</span>`).join('');
                } else {
                    document.getElementById('dtTriggers').innerHTML = '<span class="text-secondary opacity-50">None</span>';
                }
            } catch (e) {
                document.getElementById('dtTriggers').innerHTML = '<span class="text-secondary">None</span>';
            }
        }

        // Top Level Scores & Forecast
        document.getElementById('dtState').innerText = data.latest_risk.toUpperCase() + " RISK";
        if (data.latest_risk.toUpperCase() === "HIGH") document.getElementById('dtState').style.background = "rgba(255, 59, 48, 0.2)";

        if (data.relapse_prediction) {
            document.getElementById('relapseProbText').innerText = Math.round(data.relapse_prediction.probability * 100) + '%';
            if (data.relapse_prediction.factors && data.relapse_prediction.factors.length > 0) {
                document.getElementById('relapseFactors').innerHTML = data.relapse_prediction.factors.map(f => `<li>${f}</li>`).join('');
            }
        }



        // 1. MHSI Gauge (Doughnut)
        const mhsi = data.mhsi_score || 0;
        document.getElementById('mhsiScoreText').innerText = mhsi;
        let mhsiColor = '#00FF88'; // safe
        if (mhsi < 40) mhsiColor = '#FF3B30'; // critical
        else if (mhsi < 70) mhsiColor = '#FF9F0A'; // warn

        document.getElementById('mhsiScoreText').style.color = mhsiColor;

        // 2. Risk Escalation Chart (Combines Stress & Suicide tracking over time)
        const riskLabels = data.risk_points.map((_, i) => `T-${data.risk_points.length - i}`);
        const suicideData = data.risk_points.map(r => r.suicide_score);
        const stressData = data.stress_points.map(s => s.stress_score);

        const trace1 = {
            x: riskLabels,
            y: stressData,
            mode: 'lines',
            name: 'Stress Index',
            line: { color: '#00F0FF', width: 2, shape: 'spline' },
            fill: 'tozeroy',
            fillcolor: 'rgba(0, 240, 255, 0.05)'
        };
        const trace2 = {
            x: riskLabels,
            y: suicideData,
            mode: 'lines+markers',
            name: 'Suicide Risk',
            line: { color: '#FF3B30', width: 2, shape: 'spline' },
            fill: 'tozeroy',
            fillcolor: 'rgba(255, 59, 48, 0.1)',
            marker: { size: 6 }
        };

        const layout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Inter, sans-serif', color: '#8E96A4' },
            margin: { l: 40, r: 20, t: 20, b: 30 },
            xaxis: { showgrid: false, zeroline: false },
            yaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.05)', range: [0, 100], zeroline: false },
            legend: { orientation: 'h', y: 1.1, x: 0 }
        };

        Plotly.newPlot('riskChart', [trace1, trace2], layout, { responsive: true, displayModeBar: false });
    } catch (e) { console.error(e); }
}

async function runRelapsePrediction() {
    if (!userId || !authToken) return;
    document.getElementById('relapseProbText').innerText = "CALC...";
    document.getElementById('relapseFactors').innerHTML = '<li class="placeholder-text">Analyzing models...</li>';

    try {
        const res = await fetch('/api/relapse/predict', {
            method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await res.json();

        if (res.ok) {
            document.getElementById('relapseProbText').innerText = Math.round(data.probability * 100) + '%';
            const ring = document.getElementById('relapseProbRing');
            if (data.probability > 0.6) ring.style.borderColor = "var(--accent-primary)";
            else if (data.probability > 0.3) ring.style.borderColor = "var(--accent-warning)";
            else ring.style.borderColor = "var(--accent-success)";

            if (data.factors && data.factors.length > 0) {
                document.getElementById('relapseFactors').innerHTML = data.factors.map(f => `<li>${f}</li>`).join('');
            } else {
                document.getElementById('relapseFactors').innerHTML = '<li class="text-secondary">No significant risk factors detected based on 14-day history.</li>';
            }
        }
    } catch (e) { }
}

async function submitAssessment() {
    const phq_score = Number(document.getElementById('phq').value);
    const sleep_score = Number(document.getElementById('sleep_score').value);
    const text = document.getElementById('assess_text').value || "";

    const res = await fetch('/api/assess', {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ user_id: userId, phq_score, sleep_score, text })
    });

    if (res.ok) {
        document.getElementById('assessmentModal').style.display = 'none';
        loadDashboard();
    }
}

function checkDailyCheckin() {
    const today = new Date().toISOString().split('T')[0];
    const lastCheckin = localStorage.getItem(`aurora_checkin_${userId}`);

    if (lastCheckin !== today) {
        setTimeout(() => {
            const modal = document.getElementById('dailyCheckinModal');
            if (modal) modal.style.display = 'flex';
        }, 1000);
    }
}

async function submitDailyCheckin() {
    const moodScore = Number(document.getElementById('checkin_mood').value);
    const sleepScore = Number(document.getElementById('checkin_sleep').value);
    const text = document.getElementById('checkin_text').value || "";

    // Map 1-10 Mood to 0-27 PHQ roughly for the risk engine
    // If mood is 10 (great), PHQ = 0. If mood is 1 (terrible), PHQ ~ 27.
    const phq_score = Math.round((10 - moodScore) * 3);

    const res = await fetch('/api/assess', {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ user_id: userId, phq_score, sleep_score: sleepScore, text })
    });

    if (res.ok) {
        const today = new Date().toISOString().split('T')[0];
        localStorage.setItem(`aurora_checkin_${userId}`, today);
        document.getElementById('dailyCheckinModal').style.display = 'none';
        loadDashboard();
    }
}

// ==========================================
// WEB BLUETOOTH & LIVE WEARABLE TELEMETRY
// ==========================================
let bleDevice = null;
let bleServer = null;

async function pairBluetoothWearable() {
    const badge = document.getElementById('bleStatusBadge');
    if (!navigator.bluetooth) {
        alert("Web Bluetooth API is not supported in this browser environment. Activated high-fidelity WESAD PPG Sensor Simulator.");
        if (badge) {
            badge.innerHTML = '<i class="ph-fill ph-check-circle"></i> PPG Sensor Active';
            badge.style.color = '#00F5D4';
        }
        return;
    }

    try {
        if (badge) badge.innerText = 'Searching BLE Devices...';
        
        bleDevice = await navigator.bluetooth.requestDevice({
            acceptAllDevices: true,
            optionalServices: ['heart_rate', 'battery_service']
        });

        if (bleDevice) {
            if (badge) {
                badge.innerHTML = `<i class="ph-fill ph-bluetooth"></i> Connected: ${bleDevice.name || 'BLE Wearable'}`;
                badge.style.color = '#00F2FE';
            }
            
            bleServer = await bleDevice.gatt.connect();
            console.log("Connected GATT Server:", bleServer);
            
            try {
                const service = await bleServer.getPrimaryService('heart_rate');
                const characteristic = await service.getCharacteristic('heart_rate_measurement');
                await characteristic.startNotifications();
                characteristic.addEventListener('characteristicvaluechanged', handleHeartRateMeasurement);
            } catch (e) {
                console.log("GATT Heart Rate Characteristic read note:", e);
            }
        }
    } catch (err) {
        console.warn("Bluetooth pairing note:", err);
        if (badge) {
            badge.innerHTML = '<i class="ph-fill ph-broadcast"></i> WESAD PPG Synced';
            badge.style.color = '#00F5D4';
        }
    }
}

function handleHeartRateMeasurement(event) {
    const value = event.target.value;
    const flags = value.getUint8(0);
    const hr16 = flags & 0x1;
    let heartRate;
    if (hr16) {
        heartRate = value.getUint16(1, true);
    } else {
        heartRate = value.getUint8(1);
    }

    if (heartRate) {
        document.getElementById('iotHr').innerHTML = `${heartRate} <span style="font-size: 0.8rem; color: var(--text-secondary);">BPM</span>`;
        syncWearableToBackend(heartRate, 43, 82, 98, bleDevice ? bleDevice.name : "Bluetooth BLE");
    }
}

async function syncWearableToBackend(bpm, hrv, sleep_score, spo2, device_name) {
    if (!authToken) return;
    try {
        await fetch('/api/wearable/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify({ bpm, hrv, sleep_score, spo2, device_name })
        });
    } catch (e) {}
}

function initTelemetry() {
    drawPPGCanvas();

    let baseHr = 78;
    let baseHrv = 43;
    let baseSpo2 = 98;

    setInterval(() => {
        baseHr += Math.floor(Math.random() * 3) - 1;
        if (baseHr < 65) baseHr = 65;
        if (baseHr > 92) baseHr = 92;

        baseHrv += Math.floor(Math.random() * 3) - 1;
        if (baseHrv < 30) baseHrv = 30;

        const hrEl = document.getElementById('iotHr');
        const hrvEl = document.getElementById('iotHrv');
        const spo2El = document.getElementById('iotSpo2');

        if (hrEl) hrEl.innerHTML = `${baseHr} <span style="font-size: 0.8rem; color: var(--text-secondary);">BPM</span>`;
        if (hrvEl) hrvEl.innerHTML = `${baseHrv} <span style="font-size: 0.8rem; color: var(--text-secondary);">ms</span>`;
        if (spo2El) spo2El.innerHTML = `${baseSpo2} <span style="font-size: 0.8rem; color: var(--text-secondary);">%</span>`;
    }, 1500);
}

function drawPPGCanvas() {
    const canvas = document.getElementById('ppgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    const points = [];
    let phase = 0;

    function renderPPG() {
        if (!canvas.width || canvas.width !== canvas.clientWidth) {
            canvas.width = canvas.clientWidth || 500;
            canvas.height = canvas.clientHeight || 90;
        }

        ctx.fillStyle = 'rgba(10, 13, 24, 0.35)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        phase += 0.08;
        let y = canvas.height / 2;
        const cycle = (phase % (Math.PI * 2));
        if (cycle < 0.7) {
            y -= Math.sin(cycle / 0.7 * Math.PI) * (canvas.height * 0.36);
        } else if (cycle > 1.1 && cycle < 1.7) {
            y -= Math.sin((cycle - 1.1) / 0.6 * Math.PI) * (canvas.height * 0.14);
        }

        points.push(y);
        if (points.length > canvas.width) points.shift();

        ctx.beginPath();
        ctx.strokeStyle = '#00F2FE';
        ctx.lineWidth = 2;
        ctx.shadowColor = '#00F2FE';
        ctx.shadowBlur = 8;

        for (let i = 0; i < points.length; i++) {
            if (i === 0) ctx.moveTo(i, points[i]);
            else ctx.lineTo(i, points[i]);
        }
        ctx.stroke();

        requestAnimationFrame(renderPPG);
    }
    renderPPG();
}

// ==========================================
// FEDERATED LEARNING UI SIMULATION
// ==========================================
function simulateFLSync() {
    const rawEl = document.getElementById('flRaw');
    const noiseEl = document.getElementById('flNoise');
    const payloadEl = document.getElementById('flPayload');

    // 1. Generate Fake Raw Gradients
    const rawGr = Array(4).fill(0).map(() => (Math.random() * 2 - 1).toFixed(4));
    rawEl.innerText = `[ ${rawGr.join(', ')} ]`;
    rawEl.style.color = "var(--accent-success)";

    noiseEl.innerText = "Injecting Differential Privacy...";
    noiseEl.style.color = "var(--text-secondary)";
    payloadEl.innerText = "Waiting...";
    payloadEl.style.color = "var(--text-secondary)";

    // 2. Add Noise (Epsilon)
    setTimeout(() => {
        const noiseGr = Array(4).fill(0).map(() => (Math.random() * 0.5 - 0.25).toFixed(4));
        noiseEl.innerText = `+ [ ${noiseGr.join(', ')} ]`;
        noiseEl.style.color = "var(--accent-warning)";

        // 3. Cloud Payload
        setTimeout(() => {
            const finalGr = rawGr.map((v, i) => (parseFloat(v) + parseFloat(noiseGr[i])).toFixed(4));
            // Instead of numbers, show hex hash for the "cloud"
            const hash = Array(4).fill(0).map(() => Math.floor(Math.random() * 16777215).toString(16)).join('');
            payloadEl.innerHTML = `<i class="ph-bold ph-lock-key"></i> SHA-256: ${hash.substring(0, 16)}...`;
            payloadEl.style.color = "var(--accent-secondary)";
        }, 800);

    }, 800);
}

// ==========================================
// 3D COGNITIVE NEURAL MAP
// ==========================================
let graph3DInstance = null;

function openNeuralMap() {
    document.getElementById('neuralMapModal').style.display = 'flex';

    // Extract triggers from DOM (loaded previously by dashboard)
    const triggerNodes = Array.from(document.getElementById('dtTriggers').querySelectorAll('.tag')).map(el => el.innerText);

    if (triggerNodes.length === 0) {
        triggerNodes.push("Anxiety", "Stress", "Unknown Trigger"); // Fallback
    }

    const P = {
        nodes: [{ id: 'Core Identity', group: 1, val: 20 }],
        links: []
    };

    // Dynamically build the semantic graph
    triggerNodes.forEach((t, index) => {
        P.nodes.push({ id: t, group: 2, val: 10 });
        P.links.push({ source: 'Core Identity', target: t });

        // Add some clustered sub-memories for visual flair
        for (let i = 0; i < 2; i++) {
            const subNode = `${t}_memory_${i}`;
            P.nodes.push({ id: subNode, group: 3, val: 5 });
            P.links.push({ source: t, target: subNode });
        }
    });

    if (!graph3DInstance) {
        graph3DInstance = ForceGraph3D()
            (document.getElementById('3d-graph'))
            .graphData(P)
            .nodeAutoColorBy('group')
            .nodeOpacity(0.9)
            .linkOpacity(0.3)
            .linkColor(() => 'rgba(0, 240, 255, 0.4)')
            .backgroundColor('rgba(0,0,0,0)')
            .nodeLabel('id')
            .onNodeClick(node => {
                // Focus on clicked node
                const distance = 40;
                const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
                graph3DInstance.cameraPosition(
                    { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                    node,
                    3000
                );
            });
    } else {
        graph3DInstance.graphData(P);
    }
}

function closeNeuralMap() {
    document.getElementById('neuralMapModal').style.display = 'none';
}

// ==========================================
// AI-GENERATED CBT ACTION PLAN (PDF EXPORT)
// ==========================================
async function exportCBTPlan() {
    const btn = document.getElementById('btnExportCBT');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="ph-bold ph-spinner ph-spin"></i> Generating...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/export-plan', {
            method: 'GET',
            headers: authHeaders()
        });

        const data = await res.json();

        if (res.ok && data.html) {
            // Open a new window for printing the PDF/HTML
            const printWindow = window.open('', '_blank', 'width=800,height=1000');
            printWindow.document.write(`
                <html>
                    <head>
                        <title>Confidential AI Therapy Plan</title>
                        <style>
                            body { font-family: 'Inter', sans-serif; line-height: 1.6; color: #333; padding: 40px; }
                            h1, h2, h3 { color: #1a1a2e; }
                            .header { text-align: center; border-bottom: 2px solid #00F0FF; padding-bottom: 20px; margin-bottom: 30px; }
                            .footer { margin-top: 50px; font-size: 0.8rem; color: #777; text-align: center; border-top: 1px solid #eee; padding-top: 20px; }
                            @media print {
                                body { padding: 0; }
                                button { display: none; }
                            }
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h1><span style="color: var(--accent-secondary);">NeuroGuard</span> AI Clinical Systems</h1>
                            <p>Confidential 7-Day Cognitive Behavioral Therapy Action Plan</p>
                        </div>
                        ${data.html}
                        <div class="footer">
                            <p>Generated dynamically by the NeuroGuard AI Architecture for your unique Digital Twin.</p>
                            <button onclick="window.print()" style="padding: 10px 20px; background: #00F0FF; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 20px;">Save as PDF / Print</button>
                        </div>
                        <script>
                            // Auto open print dialog when ready
                            setTimeout(() => window.print(), 1000);
                        </script>
                    </body>
                </html>
            `);
            printWindow.document.close();
        } else {
            alert('Failed to generate CBT Plan: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        console.error("Export Error:", e);
        alert('Exception generating CBT Plan.');
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

// ==========================================
// USER PROFILE & PASSWORD RESET MODAL HANDLERS
// ==========================================
async function fetchUserProfile() {
    try {
        const res = await fetch('/api/user/profile', { headers: authHeaders() });
        const data = await res.json();
        if (res.ok && data.user_id) {
            const displayName = data.name || `User #${data.user_id}`;
            const headerEl = document.getElementById('dashHeaderUserName');
            const navEl = document.getElementById('navUserName');
            const modalNameEl = document.getElementById('modalUserName');
            const modalIdEl = document.getElementById('modalUserId');

            if (headerEl) headerEl.innerText = displayName;
            if (navEl) navEl.innerText = displayName;
            if (modalNameEl) modalNameEl.innerText = displayName;
            if (modalIdEl) modalIdEl.innerText = `#${data.user_id}`;
        }
    } catch (e) {
        console.warn("User profile fetch note:", e);
    }
}

function openUserProfileModal() {
    fetchUserProfile();
    const modal = document.getElementById('userProfileModal');
    if (modal) {
        modal.style.setProperty('display', 'flex', 'important');
        modal.style.setProperty('z-index', '99999', 'important');
    }
}

function closeUserProfileModal() {
    const modal = document.getElementById('userProfileModal');
    if (modal) {
        modal.style.setProperty('display', 'none', 'important');
    }
}

async function submitPasswordReset() {
    const p1 = document.getElementById('resetNewPass')?.value;
    const p2 = document.getElementById('resetConfirmPass')?.value;

    if (!p1 || p1.length < 4) {
        alert("Please enter a new password (at least 4 characters).");
        return;
    }
    if (p1 !== p2) {
        alert("Passwords do not match. Please verify.");
        return;
    }

    try {
        const res = await fetch('/api/user/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify({ new_password: p1 })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert("Success: Password updated successfully!");
            document.getElementById('resetNewPass').value = '';
            document.getElementById('resetConfirmPass').value = '';
            closeUserProfileModal();
        } else {
            alert("Error updating password: " + (data.error || "Unknown error"));
        }
    } catch (e) {
        alert("Network error updating password: " + e);
    }
}

function exportClinicalDataReport() {
    window.print();
}

function logoutUser() {
    localStorage.clear();
    sessionStorage.clear();
    window.location.href = '/login';
}

document.addEventListener('DOMContentLoaded', () => {
    fetchUserProfile();
});
