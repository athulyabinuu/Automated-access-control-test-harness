from flask import Blueprint, render_template
from flask_login import login_required
from models.user import User
from models.department import Department
from models.order import Order
from models.document import Document
from models.ticket import Ticket
from models.report import Report
from utils.decorators import role_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@role_required('Admin')
def index():
    users_count = User.query.count()
    depts_count = Department.query.count()
    orders_count = Order.query.count()
    docs_count = Document.query.count()
    tickets_count = Ticket.query.count()
    reports_count = Report.query.count()

    system_users = User.query.order_by(User.id.asc()).all()

    return render_template(
        'admin.html',
        users_count=users_count,
        depts_count=depts_count,
        orders_count=orders_count,
        docs_count=docs_count,
        tickets_count=tickets_count,
        reports_count=reports_count,
        system_users=system_users
    )
