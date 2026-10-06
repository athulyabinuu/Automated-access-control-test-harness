from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.department import Department
from utils.decorators import role_required

users_bp = Blueprint('users', __name__)

@users_bp.route('/users')
@login_required
def index():
    users = User.query.order_by(User.id.asc()).all()
    departments = Department.query.all()
    return render_template('users.html', users=users, departments=departments)

@users_bp.route('/users/create', methods=['POST'])
@login_required
@role_required('Admin')
def create_user():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'User')
    department_id = request.form.get('department_id', type=int)

    if not username or not email or not password:
        flash('Username, email, and password are required.', 'danger')
        return redirect(url_for('users.index'))

    if User.query.filter((User.username == username) | (User.email == email)).first():
        flash('Username or email already exists.', 'danger')
        return redirect(url_for('users.index'))

    new_user = User(username=username, email=email, role=role, department_id=department_id)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()
    flash(f'User "{username}" created successfully with role "{role}".', 'success')
    return redirect(url_for('users.index'))

@users_bp.route('/users/<int:user_id>/update-role', methods=['POST'])
@login_required
@role_required('Admin')
def update_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')

    if new_role not in ['User', 'Manager', 'Admin']:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('users.index'))

    user.role = new_role
    db.session.commit()
    flash(f'Role for "{user.username}" updated to "{new_role}".', 'success')
    return redirect(url_for('users.index'))

@users_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_user(user_id):
    if current_user.id == user_id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('users.index'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.username}" deleted successfully.', 'success')
    return redirect(url_for('users.index'))
