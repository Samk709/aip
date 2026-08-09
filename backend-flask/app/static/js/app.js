let userId = null;
let authToken = null;
let userName = "Guest";

function authHeaders() {
  return authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
}

function updateNavUser(name) {
  document.getElementById('navUserName').innerText = name;
}

async function registerUser() {
  const nameInput = document.getElementById('name').value || "User";
  const payload = {
    name: nameInput,
    email: document.getElementById('email').value,
    password: document.getElementById('password').value,
    preferred_language: document.getElementById('lang').value,
  };
  const res = await fetch('/api/auth/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!res.ok) return alert(data.error || 'register failed');
  userId = data.user_id;
  document.getElementById('uid').innerText = `Registered User ID: ${userId} - Please Login`;
  document.getElementById('uid').style.color = 'var(--accent-success)';
}

async function loginUser() {
  const payload = {
    email: document.getElementById('email').value,
    password: document.getElementById('password').value,
  };
  const res = await fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!res.ok) {
    document.getElementById('uid').innerText = data.error || 'Login failed';
    document.getElementById('uid').style.color = 'var(--accent-primary)';
    return;
  }
  authToken = data.token;
  userId = data.user_id;
  updateNavUser("Authenticated User");

  transitionToDashboard();
}

async function loginAnonymous() {
  const res = await fetch('/api/auth/anonymous', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }
  });
  const data = await res.json();
  if (!res.ok) return alert(data.error || 'anonymous login failed');
  authToken = data.token;
  userId = data.user_id;
  updateNavUser(data.name || "Guest User");

  transitionToDashboard();
}

function transitionToDashboard() {
  document.getElementById('loginOverlay').style.opacity = '0';
  setTimeout(() => {
    document.getElementById('loginOverlay').style.display = 'none';
    document.getElementById('appDashboard').style.display = 'flex';
    loadDashboard();
    startWebcam(); // Warn user camera might be requested securely
  }, 400);
}

// ==========================================
// VOICE DICTATION & WEB SPEECH API
// ==========================================
let recognition = null;
if ('webkitSpeechRecognition' in window) {
  recognition = new webkitSpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onresult = function (event) {
    let transcript = event.results[0][0].transcript;
    const msgInput = document.getElementById('msg');
    msgInput.value += (msgInput.value ? ' ' : '') + transcript;
    document.getElementById('voiceBtn').classList.remove('glow-card');
    document.getElementById('voiceBtn').style.borderColor = 'var(--glass-border)';
  };
  recognition.onerror = function (event) {
    console.error("Speech recognition error", event.error);
    document.getElementById('voiceBtn').classList.remove('glow-card');
    document.getElementById('voiceBtn').style.borderColor = 'var(--glass-border)';
  };
} else {
  console.warn("Speech Recognition API not supported in this browser.");
}

function toggleVoice() {
  if (!recognition) { alert("Voice dictation not supported in this browser."); return; }
  const btn = document.getElementById('voiceBtn');
  btn.classList.add('glow-card');
  btn.style.borderColor = 'var(--accent-primary)';
  recognition.start();
}

// ==========================================
// BIOMARKER TRACKING SYSTEM & VISUALIZER
// ==========================================
let lastKeyTime = Date.now();
let keyPresses = 0;
let typingSpeedWpm = 0;
let messageStartTime = 0;
let backspaceCount = 0;

let wpmHistory = Array(15).fill(0);
let keystrokeChartInstance = null;

function updateKeystrokeChart(wpm) {
  wpmHistory.shift();
  wpmHistory.push(wpm);
  if (keystrokeChartInstance) {
    keystrokeChartInstance.update();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadFaceModels(); // Load massive AI models asynchronously on background

  const msgInput = document.getElementById('msg');
  if (msgInput) {
    msgInput.addEventListener('focus', () => {
      if (messageStartTime === 0) messageStartTime = Date.now();
    });

    msgInput.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace') {
        backspaceCount++;
      }
    });

    msgInput.addEventListener('input', () => {
      keyPresses++;
      const now = Date.now();
      const elapsedMinutes = (now - lastKeyTime) / 60000;
      if (elapsedMinutes > 0.01) { // recalculate every ~0.6 seconds
        typingSpeedWpm = (keyPresses / 5) / elapsedMinutes;
        updateKeystrokeChart(typingSpeedWpm);
        // Reset for moving average
        keyPresses = 0;
        lastKeyTime = now;
      }
    });
  }
});

async function submitBiomarkers() {
  if (!userId || !authToken) return;

  const hesitationMs = messageStartTime ? Date.now() - messageStartTime : 0;
  const hour = new Date().getHours();
  const isLateNight = (hour >= 1 && hour <= 5);
  const finalWpm = Math.min(Math.max(typingSpeedWpm, 0), 120);

  const payload = {
    user_id: userId,
    typing_speed_wpm: finalWpm,
    hesitation_time_ms: hesitationMs,
    backspace_count: backspaceCount,
    is_late_night: isLateNight
  };

  try {
    const res = await fetch('/api/biomarkers', {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    const consoleEl = document.getElementById('biomarkerConsole');
    if (consoleEl) {
      consoleEl.innerHTML = `> Sync complete. Telemetry Distress Weight: ${(data.distress_score * 100).toFixed(1)}%<br>` + consoleEl.innerHTML;
    }
  } catch (e) { }

  // Reset Tracking
  keyPresses = 0;
  lastKeyTime = Date.now();
  typingSpeedWpm = 0;
  messageStartTime = 0;
  backspaceCount = 0;
}


// ==========================================
// API CALLS
// ==========================================
async function assess() {
  if (!userId || !authToken) return alert('Register and login first');
  const phq_score = Number(document.getElementById('phq').value);
  const sleep_score = Number(document.getElementById('sleep_score').value);

  document.getElementById('assessmentResult').innerText = "> PROCESSING ASSESSMENT...";

  const res = await fetch('/api/assess', {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ user_id: userId, phq_score, sleep_score })
  });
  const data = await res.json();
  document.getElementById('assessmentResult').innerText = `> ASSESSMENT COMPLETE.\n> RISK_LEVEL: ${data.risk_level}\n> SEVERITY: ${data.severity}\n> SUICIDE_RISK_INDEX: ${data.suicide_risk_score}`;
  loadDashboard(); // Refresh graphs
}

async function runRelapsePrediction() {
  if (!userId || !authToken) return;
  document.getElementById('relapseProbText').innerText = "CALC...";
  document.getElementById('relapseFactors').innerHTML = '<li class="placeholder-text">Analyzing models...</li>';

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
}

async function triggerFederatedSync() {
  if (!document.getElementById('flToggle').checked) {
    return alert("Privacy-Preserving Edge Mode is disabled. Enable it to simulate secure sync.");
  }

  const con = document.getElementById('flConsole');
  con.innerHTML = "> Generating local differential gradient...<br>" + con.innerHTML;

  // Simulate some work
  setTimeout(async () => {
    // Send pseudo weights
    const res = await fetch('/api/fl/aggregate', {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ user_id: userId, weights: "0.01,-0.002,0.553,0.1" })
    });
    const data = await res.json();

    if (res.ok) {
      con.innerHTML = `> SYNC SUCCESS. Encrypted Edge Checksum: <span class="text-success">${data.hash}</span><br>` + con.innerHTML;
    } else {
      con.innerHTML = `> SYNC FAILED.<br>` + con.innerHTML;
    }
  }, 800);
}


async function chat() {
  if (typeof ensureActiveSession === 'function') {
    await ensureActiveSession();
  }
  const messageInput = document.getElementById('msg');
  const message = messageInput ? messageInput.value.trim() : '';
  if (!message) return;

  if (typeof submitBiomarkers === 'function') {
    submitBiomarkers();
  }

  const chatBox = document.getElementById('chatResult');

  // Format User Message
  chatBox.innerHTML += `
    <div class="message user-message">
        <div class="msg-header"><i class="ph-bold ph-user"></i> YOU</div>
        <div class="msg-body">${message}</div>
    </div>`;
  messageInput.value = '';

  const res = await fetch('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ user_id: userId, message })
  });

  const data = await res.json();

  // Parse AI Markdown Reply
  const parsedReply = marked.parse(data.reply);

  // Format AI Message
  chatBox.innerHTML += `
    <div class="message ai-message glow-card">
        <div class="msg-header text-success"><i class="ph-fill ph-brain"></i> Smart Mental Health Companion Using AI</div>
        <div class="msg-body markdown-body">${parsedReply}</div>
        <div class="msg-footer">
            <span class="system-tag"><i class="ph-bold ph-shield-check"></i> Risk: ${data.risk_level}</span>
            <span class="system-tag"><i class="ph-bold ph-activity"></i> Sentiment: ${data.sentiment}</span>
        </div>
    </div>`;

  chatBox.scrollTop = chatBox.scrollHeight;

  if (data.digital_twin_triggers) {
    document.getElementById('memoryContextBox').innerText = data.digital_twin_triggers;
  }

  if (data.show_emergency_contacts || data.emergency_alert) {
    document.getElementById('emergencyBanner').style.display = 'flex';
  } else {
    document.getElementById('emergencyBanner').style.display = 'none';
  }

  if (data.xai_explanation && data.xai_explanation.includes("ALERT:")) {
    document.getElementById('driftAlertBanner').style.display = 'flex';
    const driftText = data.xai_explanation.split("ALERT:")[1].replace("]", "");
    document.getElementById('driftAlertText').innerText = driftText;
  } else {
    document.getElementById('driftAlertBanner').style.display = 'none';
  }

  // Recommendations
  if (data.recommendations && data.recommendations.length > 0) {
    const recsPanel = document.getElementById('recommendationsPanel');
    const recsContainer = document.getElementById('recsContainer');
    recsContainer.innerHTML = '';
    recsPanel.style.display = 'block';
    data.recommendations.forEach(r => {
      const div = document.createElement('div');
      div.className = 'glass-card';
      div.style.padding = '8px';
      div.style.fontSize = '0.8rem';
      div.innerHTML = `<strong class="text-success">${r.title}</strong><br><small class="text-secondary">${r.description}</small>`;
      recsContainer.appendChild(div);
    });
  } else {
    document.getElementById('recommendationsPanel').style.display = 'none';
  }
}

// ==========================================
// CHARTS & DASHBOARD RENDERING
// ==========================================
let riskChartInstance = null;
let mhsiChartInstance = null;

async function loadDashboard() {
  if (!userId || !authToken) return;
  const res = await fetch(`/api/dashboard/${userId}`, {
    headers: { 'Authorization': `Bearer ${authToken}` }
  });
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

  Chart.defaults.color = '#8E96A4';
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';

  // 1. MHSI Gauge (Doughnut)
  const mhsi = data.mhsi_score || 0;
  document.getElementById('mhsiScoreText').innerText = mhsi;
  let mhsiColor = '#00FF88'; // safe
  if (mhsi < 40) mhsiColor = '#FF3B30'; // critical
  else if (mhsi < 70) mhsiColor = '#FF9F0A'; // warn

  document.getElementById('mhsiScoreText').style.color = mhsiColor;

  const ctxMhsi = document.getElementById('mhsiChart').getContext('2d');
  if (mhsiChartInstance) mhsiChartInstance.destroy();
  mhsiChartInstance = new Chart(ctxMhsi, {
    type: 'doughnut',
    data: {
      labels: ['MHSI', 'Gap'],
      datasets: [{
        data: [mhsi, 100 - mhsi],
        backgroundColor: [mhsiColor, 'rgba(255,255,255,0.05)'],
        borderWidth: 0,
        circumference: 180,
        rotation: 270,
        cutout: '80%',
        borderRadius: 5
      }]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { enabled: false } } }
  });

  // 2. Risk Escalation Chart (Combines Stress & Suicide tracking over time)
  const riskLabels = data.risk_points.map((_, i) => `T-${data.risk_points.length - i}`);
  const suicideData = data.risk_points.map(r => r.suicide_score);
  const stressData = data.stress_points.map(s => s.stress_score);

  const ctxRisk = document.getElementById('riskChart').getContext('2d');
  if (riskChartInstance) riskChartInstance.destroy();
  riskChartInstance = new Chart(ctxRisk, {
    type: 'line',
    data: {
      labels: riskLabels,
      datasets: [
        {
          label: 'Stress Index',
          data: stressData,
          borderColor: '#00F0FF',
          backgroundColor: 'rgba(0, 240, 255, 0.05)',
          tension: 0.4,
          fill: true,
          pointRadius: 2
        },
        {
          label: 'Suicide Escalation Risk',
          data: suicideData,
          borderColor: '#FF3B30',
          backgroundColor: 'rgba(255, 59, 48, 0.1)',
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, max: 100 },
        x: { grid: { display: false } }
      },
      plugins: {
        legend: { position: 'top', align: 'end', labels: { boxWidth: 10, usePointStyle: true } }
      }
    }
  });
  // 3. Keystroke Dynamics Line Chart
  const ctxKey = document.getElementById('keystrokeChart');
  if (ctxKey) {
    if (keystrokeChartInstance) keystrokeChartInstance.destroy();
    keystrokeChartInstance = new Chart(ctxKey.getContext('2d'), {
      type: 'line',
      data: {
        labels: Array(15).fill(''),
        datasets: [{
          label: 'Live Speed (WPM)',
          data: wpmHistory,
          borderColor: '#FF9F0A',
          backgroundColor: 'rgba(255, 159, 10, 0.1)',
          tension: 0.3,
          fill: true,
          pointRadius: 0,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 }, // For real-time feel
        scales: {
          y: { title: { display: false }, display: true, min: 0, max: 120 },
          x: { display: false }
        },
        plugins: { legend: { display: false } }
      }
    });
  }
}

// ==========================================
// WEBCAM & EDGE BIO-SCANNER (face-api.js)
// ==========================================
let videoStream = null;
let modelsLoaded = false;
let liveScanInterval = null;

async function loadFaceModels() {
  try {
    const MODEL_URL = 'https://justadudewhohacks.github.io/face-api.js/models';
    await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
    await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);
    await faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL);
    modelsLoaded = true;
    const statusBadge = document.getElementById('faceApiModelStatus');
    if (statusBadge) {
      statusBadge.innerText = "MODELS LOADED SUCCESSFULLY";
      statusBadge.style.color = "var(--accent-success)";
      statusBadge.style.background = "rgba(0, 255, 136, 0.1)";
    }
  } catch (error) {
    console.error("Failed to load edge AI models", error);
    const statusBadge = document.getElementById('faceApiModelStatus');
    if (statusBadge) {
      statusBadge.innerText = "MODEL LOAD FAILED";
      statusBadge.style.color = "var(--accent-primary)";
    }
  }
}

async function startWebcam() {
  const video = document.getElementById('webcam');
  try {
    videoStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = videoStream;
  } catch (err) { console.error("Webcam blocked or not found.", err); }
}

async function startLiveScan() {
  if (!modelsLoaded) return alert("Edge AI Models are still loading, please wait...");
  if (!videoStream) await startWebcam();

  document.getElementById('reportContainer').style.display = 'block';
  document.getElementById('repEmotion').innerText = "LOCKING ON...";
  document.getElementById('repEmotion').style.color = "var(--accent-warning)";
  document.getElementById('startLiveScanBtn').style.display = 'none'; // hide start button

  const video = document.getElementById('webcam');
  const canvas = document.getElementById('snapshot');

  // Wait until video is actually ready
  if (video.videoWidth === 0) {
    setTimeout(startLiveScan, 500);
    return;
  }

  const displaySize = { width: video.videoWidth, height: video.videoHeight };
  canvas.width = displaySize.width;
  canvas.height = displaySize.height;
  faceapi.matchDimensions(canvas, displaySize);

  let emotionHistory = [];
  const HISTORY_SIZE = 10;

  liveScanInterval = setInterval(async () => {
    if (video.paused || video.ended) return;

    // Detect
    const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceExpressions();
    const resizedDetections = faceapi.resizeResults(detections, displaySize);

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw landmarks and face box directly on webcam feed
    faceapi.draw.drawDetections(canvas, resizedDetections);
    faceapi.draw.drawFaceLandmarks(canvas, resizedDetections);

    if (detections.length > 0 && detections[0].detection.score > 0.4) {
      const expressions = detections[0].expressions;
      emotionHistory.push(expressions);
      if (emotionHistory.length > HISTORY_SIZE) emotionHistory.shift();

      // Aggregate expressions
      let sums = {};
      emotionHistory.forEach(exp => {
          Object.keys(exp).forEach(key => {
              sums[key] = (sums[key] || 0) + exp[key];
          });
      });

      let maxE = Object.keys(sums).reduce((a, b) => sums[a] > sums[b] ? a : b);
      let avgProb = sums[maxE] / emotionHistory.length;

      document.getElementById('repEmotion').innerText = maxE.toUpperCase() + ` (${(avgProb * 100).toFixed(1)}%)`;
      document.getElementById('repEmotion').style.color = "var(--accent-success)";

      let summary = `> Detected ${detections.length} face(s).<br>> Real-Time Edge Processing: Active<br>> Landmarks Extracted: 68 points.<br>> Dominant Signal: ${maxE} (Smoothed).`;
      document.getElementById('repProblems').innerHTML = summary;
    } else {
      emotionHistory = []; // Reset history if face is lost
      document.getElementById('repEmotion').innerText = "POOR LIGHTING / NO CLEAR FACE";
      document.getElementById('repEmotion').style.color = "var(--accent-warning)";
    }
  }, 150); // running at ~6.6 fps
}
