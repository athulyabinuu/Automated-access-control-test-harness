from datetime import datetime
from models import db

class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Open')  # Open, In Progress, Resolved, Closed
    priority = db.Column(db.String(30), nullable=False, default='Medium')  # Low, Medium, High, Critical
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by], back_populates='tickets_created')
    assignee = db.relationship('User', foreign_keys=[assigned_to], back_populates='tickets_assigned')

    def to_dict(self):
        return {
            'id': self.id,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else 'Unknown',
            'assigned_to': self.assigned_to,
            'assignee_name': self.assignee.username if self.assignee else 'Unassigned',
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
