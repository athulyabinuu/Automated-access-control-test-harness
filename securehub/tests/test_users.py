def test_user_cannot_create_user(client):
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})
    response = client.post('/users/create', data={
        'username': 'attacker',
        'email': 'attacker@test.com',
        'password': 'password123',
        'role': 'Admin'
    })
    assert response.status_code == 403

def test_admin_can_create_user(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    response = client.post('/users/create', data={
        'username': 'newuser',
        'email': 'newuser@test.com',
        'password': 'password123',
        'role': 'User'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'newuser' in response.data
