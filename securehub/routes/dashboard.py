from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models.user import User
from models.department import Department
from models.order import Order
from models.document import Document
from models.ticket import Ticket
from models.report import Report
from models.notification import Notification

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    total_users = User.query.count()
    total_departments = Department.query.count()
    total_orders = Order.query.count()
    total_documents = Document.query.count()
    open_tickets = Ticket.query.filter(Ticket.status.in_(['Open', 'In Progress'])).count()
    total_reports = Report.query.count()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total_users=total_users,
        total_departments=total_departments,
        total_orders=total_orders,
        total_documents=total_documents,
        open_tickets=open_tickets,
        total_reports=total_reports,
        recent_orders=recent_orders,
        user_notifications=user_notifications,
        recent_tickets=recent_tickets
    )
