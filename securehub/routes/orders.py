import random
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from models import db
from models.order import Order
from models.department import Department

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/orders')
@login_required
def index():
    if current_user.role in ['Manager', 'Admin']:
        orders = Order.query.order_by(Order.created_at.desc()).all()
    else:
        # Normal User: orders owned by user or in user's department
        if current_user.department_id:
            orders = Order.query.filter(
                (Order.user_id == current_user.id) | (Order.department_id == current_user.department_id)
            ).order_by(Order.created_at.desc()).all()
        else:
            orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()

    departments = Department.query.all()
    return render_template('orders.html', orders=orders, departments=departments)

@orders_bp.route('/orders/<int:order_id>')
@login_required
def view_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Ownership authorization check
    if current_user.role not in ['Manager', 'Admin']:
        if order.user_id != current_user.id and order.department_id != current_user.department_id:
            return render_template('errors/403.html'), 403

    return render_template('orders.html', view_single=order)

@orders_bp.route('/orders/create', methods=['POST'])
@login_required
def create_order():
    description = request.form.get('description', '').strip()
    dept_id = request.form.get('department_id', type=int) or current_user.department_id

    if not description:
        flash('Order description is required.', 'danger')
        return redirect(url_for('orders.index'))

    order_num = f"ORD-2026-{random.randint(100, 999)}"
    new_order = Order(
        user_id=current_user.id,
        department_id=dept_id,
        order_number=order_num,
        description=description,
        status='Pending'
    )
    db.session.add(new_order)
    db.session.commit()
    flash(f'Order {order_num} submitted successfully.', 'success')
    return redirect(url_for('orders.index'))
