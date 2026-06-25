from datetime import date
from app.extensions import db


class TrainingRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), default='Formation')
    provider = db.Column(db.String(160), default='')
    completed_on = db.Column(db.Date)
    expires_on = db.Column(db.Date)
    status = db.Column(db.String(40), default='planned')
    note = db.Column(db.Text, default='')
    user = db.relationship('User')

    @property
    def is_expired(self):
        return bool(self.expires_on and self.expires_on < date.today())

    @property
    def is_due_soon(self):
        if not self.expires_on:
            return False
        days_left = (self.expires_on - date.today()).days
        return 0 <= days_left <= 60


class HabilitationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    level = db.Column(db.String(80), default='')
    issued_on = db.Column(db.Date)
    expires_on = db.Column(db.Date)
    status = db.Column(db.String(40), default='valid')
    note = db.Column(db.Text, default='')
    user = db.relationship('User')

    @property
    def is_expired(self):
        return bool(self.expires_on and self.expires_on < date.today())

    @property
    def is_due_soon(self):
        if not self.expires_on:
            return False
        days_left = (self.expires_on - date.today()).days
        return 0 <= days_left <= 60
