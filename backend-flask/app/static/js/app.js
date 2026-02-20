let userId = null;
let authToken = null;
let streamRef = null;

function authHeaders() { return authToken ? { 'Authorization': `Bearer ${authToken}` } : {}; }
function showToast(msg) {
  const wrap = document.getElementById('toastContainer');
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerText = msg;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}
function addBubble(text, role) {
  const win = document.getElementById('chatWindow');
  const b = document.createElement('div');
  b.className = `bubble ${role}`;
  b.innerText = text;
  win.appendChild(b);
  win.scrollTop = win.scrollHeight;
}

async function registerUser() {
  const payload = {
    name: document.getElementById('name').value,
    email: document.getElementById('email').value,
    password: document.getElementById('password').value,
    preferred_language: document.getElementById('lang').value,
  };
  const res = await fetch('/api/auth/register', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const data = await res.json();
  if (!res.ok) return showToast(data.error || 'Register failed');
  userId = data.user_id;
  document.getElementById('uid').innerText = `Registered: #${userId}`;
  showToast('Registration successful');
}

async function loginUser() {
  const payload = { email: document.getElementById('email').value, password: document.getElementById('password').value };
  const res = await fetch('/api/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const data = await res.json();
  if (!res.ok) return showToast(data.error || 'Login failed');
  authToken = data.token; userId = data.user_id;
  document.getElementById('uid').innerText = `Logged in: #${userId}`;
  document.getElementById('statusPill').innerText = `Logged in (${data.role})`;
  showToast('Login successful');
}

async function assess() {
  if (!userId || !authToken) return showToast('Login first');
  const phq_score = Number(document.getElementById('phq').value);
  const res = await fetch('/api/assess', { method:'POST', headers:{'Content-Type':'application/json', ...authHeaders()}, body: JSON.stringify({ user_id:userId, phq_score }) });
  const data = await res.json();
  document.getElementById('assessmentResult').innerText = JSON.stringify(data, null, 2);
  document.getElementById('riskBadge').innerText = `Risk: ${data.risk_level || 'unknown'}`;
  showToast(`Assessment completed: ${data.risk_level || 'n/a'}`);
}

async function startCamera() {
  try {
    streamRef = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    document.getElementById('cam').srcObject = streamRef;
    showToast('Camera started');
  } catch (_) {
    showToast('Unable to access camera');
  }
}

async function analyzeFrame() {
  if (!authToken || !userId) return showToast('Login first');
  const video = document.getElementById('cam');
  if (!video.srcObject) return showToast('Start camera first');
  const canvas = document.getElementById('frameCanvas');
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const frame = canvas.toDataURL('image/jpeg', 0.8);

  const res = await fetch('/api/media/analyze-frame', {
    method:'POST', headers:{'Content-Type':'application/json', ...authHeaders()}, body: JSON.stringify({ frame })
  });
  const data = await res.json();
  const emotion = data?.face?.emotion || 'unknown';
  document.getElementById('faceResult').innerText = `Emotion: ${emotion}`;
  document.getElementById('face').value = emotion;
  showToast(`Detected face emotion: ${emotion}`);
}

async function analyzeMultimodal() {
  if (!userId || !authToken) return showToast('Login first');
  const payload = {
    user_id: userId,
    text: document.getElementById('msg').value,
    face_emotion: document.getElementById('face').value,
    voice_energy: Number(document.getElementById('energy').value),
    voice_pitch_var: Number(document.getElementById('pitch').value),
  };
  const res = await fetch('/api/multimodal/analyze', { method:'POST', headers:{'Content-Type':'application/json', ...authHeaders()}, body: JSON.stringify(payload) });
  const data = await res.json();
  document.getElementById('multiResult').innerText = JSON.stringify(data, null, 2);
  showToast(`Fused distress score: ${data.fused_distress_score ?? 'n/a'}`);
}

async function chat() {
  if (!userId || !authToken) return showToast('Login first');
  const message = document.getElementById('msg').value;
  addBubble(message, 'user');
  const res = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json', ...authHeaders()}, body: JSON.stringify({ user_id:userId, message }) });
  const data = await res.json();
  addBubble(data.reply || '...', 'bot');
  showToast(`Bot provider: ${data.provider || 'local'}`);
}
