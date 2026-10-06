from datetime import datetime
from models import db

class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', back_populates='documents')

    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'owner_name': self.owner.username if self.owner else 'Unknown',
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
