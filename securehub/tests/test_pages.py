import pytest

@pytest.mark.parametrize('endpoint', [
    '/dashboard',
    '/profile',
    '/users',
    '/departments',
    '/orders',
    '/documents',
    '/tickets',
    '/reports',
    '/notifications',
    '/settings'
])
def test_all_pages_load_for_authenticated_user(client, endpoint):
    client.post('/login', data={'username': 'alice', 'password': 'alice123'})
    response = client.get(endpoint)
    assert response.status_code == 200
