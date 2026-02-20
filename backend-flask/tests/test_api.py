import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app


def _register_and_login(client, email, role="user"):
    reg = client.post('/api/auth/register', json={
        'email': email,
        'password': 'pass1234',
        'name': 'Tester',
        'preferred_language': 'en',
        'role': role,
    })
    assert reg.status_code == 201

    login = client.post('/api/auth/login', json={
        'email': email,
        'password': 'pass1234',
    })
    assert login.status_code == 200
    data = login.get_json()
    return data['user_id'], {'Authorization': f"Bearer {data['token']}"}


def test_health():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.get_json()['status'] == 'ok'


def test_auth_and_assess_chat_flow():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    user_id, headers = _register_and_login(client, 'test@example.com', role='user')

    assess_resp = client.post('/api/assess', headers=headers, json={'user_id': user_id, 'phq_score': 14})
    assess = assess_resp.get_json()
    assert assess_resp.status_code == 200
    assert assess['severity'] == 'Moderate/Severe'
    assert assess['risk_level'] == 'High'

    mod_resp = client.post('/api/moderation/check', headers=headers, json={'text': 'I feel hopeless'})
    assert mod_resp.status_code == 200
    assert mod_resp.get_json()['local']['is_crisis'] is True

    multi_resp = client.post('/api/multimodal/analyze', headers=headers, json={
        'user_id': user_id,
        'text': 'I feel very stressed',
        'face_emotion': 'sad',
        'voice_energy': 0.8,
        'voice_pitch_var': 0.6,
    })
    assert multi_resp.status_code == 200
    assert multi_resp.get_json()['face_emotion'] == 'sad'

    media_resp = client.post('/api/media/analyze', headers=headers, json={})
    assert media_resp.status_code == 200

    frame_resp = client.post('/api/media/analyze-frame', headers=headers, json={'frame': 'invalid'})
    assert frame_resp.status_code == 200

    media_trained = client.post('/api/media/predict-trained', headers=headers, json={
        'face_features': [0.2] * 8,
        'voice_features': [0.3] * 8,
    })
    assert media_trained.status_code == 200

    chat_resp = client.post('/api/chat', headers=headers, json={'user_id': user_id, 'message': 'I feel very sad and anxious'})
    chat = chat_resp.get_json()
    assert chat_resp.status_code == 200
    assert chat['sentiment'] == 'negative'
    assert chat['provider'] in {'local', 'gpt', 'rasa'}


def test_rbac_admin_only_endpoint():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    _, user_headers = _register_and_login(client, 'user@example.com', role='user')
    _, admin_headers = _register_and_login(client, 'admin@example.com', role='admin')

    forbidden = client.get('/api/admin/users', headers=user_headers)
    assert forbidden.status_code == 403

    ok = client.get('/api/admin/users', headers=admin_headers)
    assert ok.status_code == 200
    assert isinstance(ok.get_json(), list)


    audit_forbidden = client.get('/api/admin/moderation-audit', headers=user_headers)
    assert audit_forbidden.status_code == 403

    counselor_id, counselor_headers = _register_and_login(client, 'counselor@example.com', role='counselor')
    assert counselor_id > 0
    audit_ok = client.get('/api/admin/moderation-audit', headers=counselor_headers)
    assert audit_ok.status_code == 200


def test_unauthorized_blocked():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    resp = client.post('/api/assess', json={'user_id': 1, 'phq_score': 5})
    assert resp.status_code == 401
