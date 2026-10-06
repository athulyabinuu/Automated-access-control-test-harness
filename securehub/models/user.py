from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='User')  # User, Manager, Admin
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    department = db.relationship('Department', back_populates='users')
    orders = db.relationship('Order', back_populates='user', lazy='dynamic')
    documents = db.relationship('Document', back_populates='owner', lazy='dynamic')
    tickets_created = db.relationship('Ticket', foreign_keys='Ticket.created_by', back_populates='creator', lazy='dynamic')
    tickets_assigned = db.relationship('Ticket', foreign_keys='Ticket.assigned_to', back_populates='assignee', lazy='dynamic')
    reports = db.relationship('Report', back_populates='creator', lazy='dynamic')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'Admin'

    @property
    def is_manager(self):
        return self.role in ['Manager', 'Admin']

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else 'N/A',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
