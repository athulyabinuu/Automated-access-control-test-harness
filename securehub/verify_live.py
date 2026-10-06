import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from models import db
from models.user import User

def run_browser_verification():
    app = create_app()
    client = app.test_client()

    with app.app_context():
        user_count = User.query.count()
        print(f"--- 1. Verify Database contains 10 users (Found: {user_count}) ---")
        assert user_count == 10, f"Expected 10 users, found {user_count}"

        expected_users = [
            ("alice", "User", "IT"),
            ("bob", "Manager", "Finance"),
            ("admin", "Admin", "IT"),
            ("charlie", "User", "HR"),
            ("david", "User", "Sales"),
            ("emma", "Manager", "HR"),
            ("frank", "User", "Finance"),
            ("grace", "User", "Sales"),
            ("henry", "Manager", "IT"),
            ("isla", "User", "Operations")
        ]

        for username, role, dept_name in expected_users:
            u = User.query.filter_by(username=username).first()
            assert u is not None, f"User {username} missing!"
            assert u.role == role, f"User {username} role mismatch: {u.role} != {role}"
            assert u.department is not None and u.department.name == dept_name, f"User {username} dept mismatch: {u.department.name if u.department else 'None'} != {dept_name}"
        print("PASS: All 10 users verified in database with exact specified role and department!")

    print("--- 2. Login as admin & verify Users page displays all 10 users ---")
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    users_page = client.get('/users')
    assert users_page.status_code == 200
    for username, _, _ in expected_users:
        assert username.encode() in users_page.data, f"Username {username} missing from Users page HTML!"
    print("PASS: Users page displays all 10 users.")
    client.post('/api/auth/logout')

    print("--- 3. Test login with required demo users: alice, bob, admin, david, emma ---")
    test_logins = [
        ("alice", "alice123", "User", "IT"),
        ("bob", "bob123", "Manager", "Finance"),
        ("admin", "admin123", "Admin", "IT"),
        ("david", "david123", "User", "Sales"),
        ("emma", "emma123", "Manager", "HR")
    ]

    for username, password, expected_role, expected_dept in test_logins:
        login_res = client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)
        assert login_res.status_code == 200, f"Login failed for {username}"
        assert username.encode() in login_res.data, f"Username {username} not found on dashboard after login"
        assert expected_role.encode() in login_res.data, f"Role {expected_role} not found on dashboard for {username}"
        print(f"PASS: Login & role display verified for user '{username}' ({expected_role}, {expected_dept}).")
        client.post('/api/auth/logout')

    print("\nALL 10 USER VERIFICATION CHECKS PASSED PERFECTLY!")

if __name__ == '__main__':
    run_browser_verification()
