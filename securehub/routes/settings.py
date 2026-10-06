from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            email = request.form.get('email', '').strip()
            if email:
                current_user.email = email
                db.session.commit()
                flash('Account email updated successfully.', 'success')
            else:
                flash('Email cannot be empty.', 'danger')

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not current_user.check_password(current_password):
                flash('Current password verification failed.', 'danger')
            elif not new_password or len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
            elif new_password != confirm_password:
                flash('New password and confirmation do not match.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password updated successfully.', 'success')

        return redirect(url_for('settings.index'))

    return render_template('settings.html')
