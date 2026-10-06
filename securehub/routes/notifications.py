from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db
from models.notification import Notification

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications')
@login_required
def index():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@notifications_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)

    # Ownership check: user can only mark their own notification as read!
    if notif.user_id != current_user.id:
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Forbidden', 'message': 'Cannot modify another user notification.'}), 403
        return render_template('errors/403.html'), 403

    notif.is_read = True
    db.session.commit()

    if request.path.startswith('/api/'):
        return jsonify({'success': True, 'message': 'Notification marked as read.'})

    flash('Notification marked as read.', 'success')
    return redirect(url_for('notifications.index'))

@notifications_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def read_all():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications.index'))
