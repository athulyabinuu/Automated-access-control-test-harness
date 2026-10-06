from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db
from models.department import Department
from utils.decorators import role_required

departments_bp = Blueprint('departments', __name__)

@departments_bp.route('/departments')
@login_required
def index():
    departments = Department.query.order_by(Department.id.asc()).all()
    return render_template('departments.html', departments=departments)

@departments_bp.route('/departments/create', methods=['POST'])
@login_required
@role_required('Manager', 'Admin')
def create_department():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('Department name is required.', 'danger')
        return redirect(url_for('departments.index'))

    if Department.query.filter_by(name=name).first():
        flash('Department already exists.', 'danger')
        return redirect(url_for('departments.index'))

    dept = Department(name=name, description=description)
    db.session.add(dept)
    db.session.commit()
    flash(f'Department "{name}" created successfully.', 'success')
    return redirect(url_for('departments.index'))
