const authToken = localStorage.getItem('aurora_token');
const userRole = localStorage.getItem('aurora_role');

function authHeaders() {
    return authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
}

if (!authToken || (userRole !== 'admin' && userRole !== 'counselor')) {
    alert("Unauthorized access. Admins only.");
    window.location.href = '/?login=true';
}

document.addEventListener('DOMContentLoaded', () => {
    loadAdminData();
});

async function loadAdminData() {
    try {
        // Fetch Users
        const userRes = await fetch('/api/admin/users', { headers: authHeaders() });
        if (userRes.ok) {
            const users = await userRes.json();
            const tbody = document.getElementById('usersTableBody');
            tbody.innerHTML = '';
            users.forEach(u => {
                tbody.innerHTML += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 10px; color: var(--text-secondary);">${u.id}</td>
                        <td style="padding: 10px;">${u.email || u.name}</td>
                        <td style="padding: 10px; color: ${u.role === 'admin' ? 'var(--accent-secondary)' : 'var(--text-primary)'};">${u.role}</td>
                    </tr>
                `;
            });
        }

        // Fetch Moderation Audit Logs
        const auditRes = await fetch('/api/admin/moderation-audit', { headers: authHeaders() });
        if (auditRes.ok) {
            const audits = await auditRes.json();
            const tbody = document.getElementById('auditTableBody');
            tbody.innerHTML = '';
            audits.forEach(a => {
                tbody.innerHTML += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 10px; color: var(--text-secondary);">${a.id}</td>
                        <td style="padding: 10px;">${a.user_id}</td>
                        <td style="padding: 10px; font-family: var(--font-mono); color: var(--accent-warning);">${a.matched_terms || 'None'}</td>
                        <td style="padding: 10px; color: ${a.is_crisis ? 'var(--accent-primary)' : 'var(--accent-success)'};">${a.is_crisis ? 'YES' : 'NO'}</td>
                    </tr>
                `;
            });
        }
    } catch (e) {
        console.error(e);
    }
}
