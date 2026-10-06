from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html', error='Invalid username or password.'), 400

    return render_template('login.html')


@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required.'}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user, remember=True)
        return jsonify({
            'success': True,
            'message': 'Login successful.',
            'user': user.to_dict()
        }), 200
    
    return jsonify({'success': False, 'message': 'Invalid username or password.'}), 401


@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    if current_user.is_authenticated:
        logout_user()
    return jsonify({
        'success': True,
        'message': 'Logout successful'
    }), 200
