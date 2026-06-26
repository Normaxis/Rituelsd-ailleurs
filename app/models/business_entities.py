from datetime import datetime, date
from app.extensions import db


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(160), default='')
    phone = db.Column(db.String(50), default='')
    birth_date = db.Column(db.Date)
    preferences = db.Column(db.Text, default='')
    allergies = db.Column(db.Text, default='')
    contraindications = db.Column(db.Text, default='')
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class GiftCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment.id'))
    amount = db.Column(db.Float, default=0)
    label = db.Column(db.String(160), default='')
    expires_on = db.Column(db.Date)
    status = db.Column(db.String(40), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('Customer')
    treatment = db.relationship('Treatment')

    @property
    def is_expired(self):
        return bool(self.expires_on and self.expires_on < date.today())


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    contact_name = db.Column(db.String(160), default='')
    email = db.Column(db.String(160), default='')
    phone = db.Column(db.String(50), default='')
    address = db.Column(db.String(255), default='')
    notes = db.Column(db.Text, default='')


class DocumentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(100), default='Procedure')
    version = db.Column(db.String(40), default='1.0')
    owner = db.Column(db.String(160), default='')
    file_url = db.Column(db.String(255), default='')
    review_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class QSEAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(100), default='Audit')
    theme = db.Column(db.String(100), default='Securite')
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default='')
    responsible = db.Column(db.String(160), default='')
    due_date = db.Column(db.Date)
    status = db.Column(db.String(40), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
