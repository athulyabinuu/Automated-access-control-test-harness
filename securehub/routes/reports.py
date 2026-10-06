from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db
from models.report import Report

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def index():
    if current_user.role in ['Manager', 'Admin']:
        reports = Report.query.order_by(Report.created_at.desc()).all()
    else:
        reports = Report.query.filter_by(created_by=current_user.id).order_by(Report.created_at.desc()).all()

    return render_template('reports.html', reports=reports)

@reports_bp.route('/reports/create', methods=['POST'])
@login_required
def create_report():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'Draft')

    if not title or not description:
        flash('Report title and description are required.', 'danger')
        return redirect(url_for('reports.index'))

    new_report = Report(
        created_by=current_user.id,
        title=title,
        description=description,
        status=status
    )
    db.session.add(new_report)
    db.session.commit()
    flash(f'Report "{title}" generated successfully.', 'success')
    return redirect(url_for('reports.index'))
