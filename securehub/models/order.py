from datetime import datetime
from models import db

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    order_number = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='orders')
    department = db.relationship('Department', back_populates='orders')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else 'Unknown',
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else 'N/A',
            'order_number': self.order_number,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
