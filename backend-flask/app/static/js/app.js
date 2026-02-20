let userId = null;
let authToken = null;

function authHeaders() {
  return authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
}

async function registerUser() {
  const payload = {
    name: document.getElementById('name').value,
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
  document.getElementById('uid').innerText = `Registered User ID: ${userId}`;
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
  if (!res.ok) return alert(data.error || 'login failed');
  authToken = data.token;
  userId = data.user_id;
  document.getElementById('uid').innerText = `Logged in User ID: ${userId}`;
}

async function assess() {
  if (!userId || !authToken) return alert('register and login first');
  const phq_score = Number(document.getElementById('phq').value);
  const res = await fetch('/api/assess', {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ user_id: userId, phq_score })
  });
  const data = await res.json();
  document.getElementById('assessmentResult').innerText = JSON.stringify(data, null, 2);
}

async function analyzeMultimodal() {
  if (!userId || !authToken) return alert('register and login first');
  const payload = {
    user_id: userId,
    text: document.getElementById('msg').value,
    face_emotion: document.getElementById('face').value,
    voice_energy: Number(document.getElementById('energy').value),
    voice_pitch_var: Number(document.getElementById('pitch').value),
  };
  const res = await fetch('/api/multimodal/analyze', {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  document.getElementById('multiResult').innerText = JSON.stringify(data, null, 2);
}

async function chat() {
  if (!userId || !authToken) return alert('register and login first');
  const message = document.getElementById('msg').value;
  const res = await fetch('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ user_id: userId, message })
  });
  const data = await res.json();
  document.getElementById('chatResult').innerText = JSON.stringify(data, null, 2);
}
