from datetime import datetime
from models import db

class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Draft')  # Draft, Published, Archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', back_populates='reports')

    def to_dict(self):
        return {
            'id': self.id,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else 'Unknown',
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
