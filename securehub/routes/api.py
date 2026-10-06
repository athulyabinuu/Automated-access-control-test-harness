from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models.user import User
from models.order import Order
from models.document import Document
from models.ticket import Ticket
from models.report import Report
from models.notification import Notification

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/users')
@login_required
def get_users():
    if current_user.role not in ['Manager', 'Admin']:
        # Restricted info for normal user
        return jsonify([{'id': u.id, 'username': u.username, 'department_name': u.department.name if u.department else 'N/A'} for u in User.query.all()])
    return jsonify([u.to_dict() for u in User.query.all()])

@api_bp.route('/api/orders')
@login_required
def get_orders():
    if current_user.role in ['Manager', 'Admin']:
        orders = Order.query.order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])

@api_bp.route('/api/documents')
@login_required
def get_documents():
    if current_user.role in ['Manager', 'Admin']:
        docs = Document.query.order_by(Document.created_at.desc()).all()
    else:
        docs = Document.query.filter_by(owner_id=current_user.id).order_by(Document.created_at.desc()).all()
    return jsonify([d.to_dict() for d in docs])

@api_bp.route('/api/documents/<int:doc_id>')
@login_required
def get_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if current_user.role not in ['Manager', 'Admin'] and doc.owner_id != current_user.id:
        return jsonify({'success': False, 'error': 'Forbidden', 'message': 'Access denied'}), 403
    return jsonify(doc.to_dict())

@api_bp.route('/api/tickets')
@login_required
def get_tickets():
    if current_user.role in ['Manager', 'Admin']:
        tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    else:
        tickets = Ticket.query.filter(
            (Ticket.created_by == current_user.id) | (Ticket.assigned_to == current_user.id)
        ).order_by(Ticket.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tickets])

@api_bp.route('/api/reports')
@login_required
def get_reports():
    if current_user.role in ['Manager', 'Admin']:
        reports = Report.query.order_by(Report.created_at.desc()).all()
    else:
        reports = Report.query.filter_by(created_by=current_user.id).order_by(Report.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reports])

@api_bp.route('/api/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifications])
