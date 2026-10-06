from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        new_email = request.form.get('email', '').strip()
        
        if new_email:
            current_user.email = new_email
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile.index'))
        else:
            flash('Email cannot be empty.', 'danger')

    return render_template('profile.html')
