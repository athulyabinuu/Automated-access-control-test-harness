def test_normal_user_cannot_access_admin(client):
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})
    response = client.get('/admin')
    assert response.status_code == 403
    assert b'Access Denied' in response.data

def test_admin_can_access_admin(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    response = client.get('/admin')
    assert response.status_code == 200
    assert b'System Administration' in response.data

def test_document_ownership_restriction(client):
    # Log in as Alice (user id 1)
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})

    # Try to access Bob's document (doc #2)
    response = client.get('/documents/2')
    assert response.status_code == 403

    # Access own document (doc #1)
    response_own = client.get('/documents/1')
    assert response_own.status_code == 200
    assert b"Incident Response Plan" in response_own.data

def test_notification_ownership_tampering_blocked(client):
    # Log in as Alice (user id 1)
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})

    # Try to mark Bob's notification (id 3) as read
    response = client.post('/notifications/3/read')
    assert response.status_code == 403
