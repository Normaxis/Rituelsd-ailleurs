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


class WaitlistEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment.id'), nullable=False)
    customer_name = db.Column(db.String(160), nullable=False)
    customer_email = db.Column(db.String(160), default='')
    customer_phone = db.Column(db.String(50), default='')
    preferred_date = db.Column(db.Date)
    preferred_period = db.Column(db.String(80), default='')
    practitioner_name = db.Column(db.String(160), default='')
    note = db.Column(db.Text, default='')
    status = db.Column(db.String(40), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    treatment = db.relationship('Treatment')


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    contact_name = db.Column(db.String(160), default='')
    email = db.Column(db.String(160), default='')
    phone = db.Column(db.String(50), default='')
    address = db.Column(db.String(255), default='')
    notes = db.Column(db.Text, default='')


class SupplierOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    reference = db.Column(db.String(100), default='')
    order_date = db.Column(db.Date)
    expected_date = db.Column(db.Date)
    received_date = db.Column(db.Date)
    status = db.Column(db.String(40), default='draft')
    total_amount = db.Column(db.Float, default=0)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    supplier = db.relationship('Supplier')


class SupplierOrderLine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('supplier_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    label = db.Column(db.String(160), default='')
    quantity = db.Column(db.Float, default=0)
    unit_price = db.Column(db.Float, default=0)
    order = db.relationship('SupplierOrder', backref='lines')
    product = db.relationship('Product')

    @property
    def line_total(self):
        return (self.quantity or 0) * (self.unit_price or 0)


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    movement_type = db.Column(db.String(40), default='adjustment')
    quantity = db.Column(db.Float, default=0)
    unit_cost = db.Column(db.Float, default=0)
    reason = db.Column(db.String(160), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product')

    @property
    def total_cost(self):
        return abs(self.quantity or 0) * (self.unit_cost or 0)


class TreatmentConsumption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Float, default=0)
    treatment = db.relationship('Treatment')
    product = db.relationship('Product')
    __table_args__ = (db.UniqueConstraint('treatment_id', 'product_id', name='uniq_treatment_product_consumption'),)


class RoutineCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routine.id'), nullable=False)
    cabin_id = db.Column(db.Integer, db.ForeignKey('cabin.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    completed_on = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(db.String(40), default='done')
    note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    routine = db.relationship('Routine')
    cabin = db.relationship('Cabin')
    user = db.relationship('User')
    __table_args__ = (db.UniqueConstraint('routine_id', 'cabin_id', 'user_id', 'completed_on', name='uniq_routine_completion_day'),)


class RoutineStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routine.id'), nullable=False)
    position = db.Column(db.Integer, default=1)
    title = db.Column(db.String(180), nullable=False)
    detail = db.Column(db.Text, default='')
    is_required = db.Column(db.Boolean, default=True)
    routine = db.relationship('Routine', backref='steps')


class RoutineReferencePhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routine.id'), nullable=False)
    title = db.Column(db.String(160), default='Reference')
    filename = db.Column(db.String(180), default='')
    mime_type = db.Column(db.String(80), default='image/jpeg')
    image_data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    routine = db.relationship('Routine', backref='reference_photos')


class RoutineProofPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    completion_id = db.Column(db.Integer, db.ForeignKey('routine_completion.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('routine_step.id'))
    kind = db.Column(db.String(40), default='proof')
    filename = db.Column(db.String(180), default='')
    mime_type = db.Column(db.String(80), default='image/jpeg')
    image_data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completion = db.relationship('RoutineCompletion', backref='proof_photos')
    step = db.relationship('RoutineStep')


class RoutineIssue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    completion_id = db.Column(db.Integer, db.ForeignKey('routine_completion.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('routine_step.id'))
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default='')
    severity = db.Column(db.String(40), default='medium')
    status = db.Column(db.String(40), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completion = db.relationship('RoutineCompletion', backref='issues')
    step = db.relationship('RoutineStep')


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
