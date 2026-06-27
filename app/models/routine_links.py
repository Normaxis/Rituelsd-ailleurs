from datetime import datetime
from app.extensions import db


class RoutineProofLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    completion_id = db.Column(db.Integer, db.ForeignKey('routine_completion.id'), nullable=False)
    title = db.Column(db.String(160), default='Preuve')
    url = db.Column(db.String(500), nullable=False)
    note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completion = db.relationship('RoutineCompletion', backref='proof_links')
