import json

def test_logout_endpoint_accepts_post(client):
    # Log in first
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})
    
    # Send logout request
    response = client.post('/api/auth/logout')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['message'] == 'Logout successful'

def test_session_cleared_after_logout(client):
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})
    
    # Verify logged in
    dash_resp = client.get('/dashboard')
    assert dash_resp.status_code == 200

    # Logout
    client.post('/api/auth/logout')

    # Dashboard should redirect to /login
    dash_resp_after = client.get('/dashboard')
    assert dash_resp_after.status_code == 302
    assert '/login' in dash_resp_after.headers['Location']

def test_duplicate_logout_no_error(client):
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})
    
    # First logout
    res1 = client.post('/api/auth/logout')
    assert res1.status_code == 200
    
    # Second logout (duplicate)
    res2 = client.post('/api/auth/logout')
    assert res2.status_code == 200
    data = json.loads(res2.data)
    assert data['success'] is True
