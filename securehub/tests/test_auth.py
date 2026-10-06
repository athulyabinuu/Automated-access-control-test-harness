def test_login_page_renders(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'SECUREHUB' in response.data

def test_valid_login(client):
    response = client.post('/login', data={
        'username': 'alice',
        'password': 'alice123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Overview Dashboard' in response.data or b'alice' in response.data

def test_invalid_login(client):
    response = client.post('/login', data={
        'username': 'alice',
        'password': 'wrongpassword'
    })
    assert response.status_code == 400
    assert b'Invalid username or password' in response.data

def test_unauthenticated_dashboard_access(client):
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_authenticated_dashboard_access(client):
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Overview Dashboard' in response.data
