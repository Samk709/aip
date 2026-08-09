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
    document.getElementById('uid').innerText = `Registered: ${data.email} - Please Login`;
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

    localStorage.setItem('aurora_token', data.token);
    localStorage.setItem('aurora_user_id', data.user_id);
    localStorage.setItem('aurora_role', data.role);
    window.location.href = '/dashboard';
}

async function loginAnonymous() {
    const res = await fetch('/api/auth/anonymous', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (!res.ok) return alert(data.error || 'anonymous login failed');

    localStorage.setItem('aurora_token', data.token);
    localStorage.setItem('aurora_user_id', data.user_id);
    localStorage.setItem('aurora_role', data.role);
    window.location.href = '/dashboard';
}

function toggleLoginModal() {
    const modal = document.getElementById('loginOverlay');
    if (modal.style.display === 'none' || !modal.style.display) {
        modal.style.display = 'flex';
        // force reflow
        void modal.offsetWidth;
        modal.style.opacity = '1';
        modal.classList.add('show');
    } else {
        modal.classList.remove('show');
        modal.style.opacity = '0';
        setTimeout(() => modal.style.display = 'none', 400);
    }
}
