from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db
from models.document import Document

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/documents')
@login_required
def index():
    if current_user.role in ['Manager', 'Admin']:
        documents = Document.query.order_by(Document.created_at.desc()).all()
    else:
        documents = Document.query.filter_by(owner_id=current_user.id).order_by(Document.created_at.desc()).all()

    return render_template('documents.html', documents=documents)

@documents_bp.route('/documents/<int:doc_id>')
@login_required
def view_document(doc_id):
    document = Document.query.get_or_404(doc_id)

    # Enforce strict ownership check for normal users
    if current_user.role not in ['Manager', 'Admin'] and document.owner_id != current_user.id:
        return render_template('errors/403.html'), 403

    if current_user.role in ['Manager', 'Admin']:
        documents = Document.query.order_by(Document.created_at.desc()).all()
    else:
        documents = Document.query.filter_by(owner_id=current_user.id).order_by(Document.created_at.desc()).all()

    return render_template('documents.html', documents=documents, active_doc=document)

@documents_bp.route('/documents/create', methods=['POST'])
@login_required
def create_document():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    content = request.form.get('content', '').strip()

    if not title or not content:
        flash('Document title and content are required.', 'danger')
        return redirect(url_for('documents.index'))

    new_doc = Document(
        owner_id=current_user.id,
        title=title,
        description=description,
        content=content
    )
    db.session.add(new_doc)
    db.session.commit()
    flash(f'Document "{title}" created successfully.', 'success')
    return redirect(url_for('documents.index'))
