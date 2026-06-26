from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)

class Institute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), default='')
    phone = db.Column(db.String(50), default='')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    institute_id = db.Column(db.Integer, db.ForeignKey('institute.id'))
    is_active = db.Column(db.Boolean, default=True)
    role = db.relationship('Role')
    institute = db.relationship('Institute')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(100), default='Massage')
    duration_minutes = db.Column(db.Integer, default=60)
    price = db.Column(db.Float, default=0)
    institute_id = db.Column(db.Integer, db.ForeignKey('institute.id'))
    is_active = db.Column(db.Boolean, default=True)
    institute = db.relationship('Institute')

class Cabin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    institute_id = db.Column(db.Integer, db.ForeignKey('institute.id'), nullable=False)
    cabin_type = db.Column(db.String(100), default='Massage solo')
    is_active = db.Column(db.Boolean, default=True)
    institute = db.relationship('Institute')

class SkillILU(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment.id'), nullable=False)
    level = db.Column(db.String(1), default='')
    user = db.relationship('User')
    treatment = db.relationship('Treatment')
    __table_args__ = (db.UniqueConstraint('user_id', 'treatment_id', name='uniq_user_treatment_ilu'),)

class WorkSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(40), default='present')
    note = db.Column(db.String(255), default='')
    user = db.relationship('User')

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(160), nullable=False)
    customer_email = db.Column(db.String(160), default='')
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cabin_id = db.Column(db.Integer, db.ForeignKey('cabin.id'), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(40), default='confirmed')
    treatment = db.relationship('Treatment')
    user = db.relationship('User')
    cabin = db.relationship('Cabin')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    unit = db.Column(db.String(20), default='ml')
    quantity = db.Column(db.Float, default=0)
    alert_threshold = db.Column(db.Float, default=0)

class Routine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    cabin_id = db.Column(db.Integer, db.ForeignKey('cabin.id'))
    instructions = db.Column(db.Text, default='')
    cabin = db.relationship('Cabin')

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    module = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')