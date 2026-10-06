from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db
from models.ticket import Ticket
from models.user import User

tickets_bp = Blueprint('tickets', __name__)

@tickets_bp.route('/tickets')
@login_required
def index():
    if current_user.role in ['Manager', 'Admin']:
        tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    else:
        tickets = Ticket.query.filter(
            (Ticket.created_by == current_user.id) | (Ticket.assigned_to == current_user.id)
        ).order_by(Ticket.created_at.desc()).all()

    assignable_users = User.query.filter(User.role.in_(['Manager', 'Admin'])).all()
    return render_template('tickets.html', tickets=tickets, assignable_users=assignable_users)

@tickets_bp.route('/tickets/create', methods=['POST'])
@login_required
def create_ticket():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'Medium')
    assigned_to = request.form.get('assigned_to', type=int)

    if not title or not description:
        flash('Ticket title and description are required.', 'danger')
        return redirect(url_for('tickets.index'))

    new_ticket = Ticket(
        created_by=current_user.id,
        assigned_to=assigned_to,
        title=title,
        description=description,
        priority=priority,
        status='Open'
    )
    db.session.add(new_ticket)
    db.session.commit()
    flash(f'Ticket "{title}" submitted successfully.', 'success')
    return redirect(url_for('tickets.index'))

@tickets_bp.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@login_required
def update_status(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')

    # Users can only update status of their own tickets or assigned tickets, unless Manager/Admin
    if current_user.role not in ['Manager', 'Admin']:
        if ticket.created_by != current_user.id and ticket.assigned_to != current_user.id:
            return render_template('errors/403.html'), 403

    if new_status in ['Open', 'In Progress', 'Resolved', 'Closed']:
        ticket.status = new_status
        db.session.commit()
        flash(f'Ticket status updated to "{new_status}".', 'success')
    else:
        flash('Invalid status.', 'danger')

    return redirect(url_for('tickets.index'))
