from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Appointment, Customer
from app.utils.auth import login_required

customers_bp = Blueprint('customers', __name__)

def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None

@customers_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        customer = Customer(first_name=request.form['first_name'], last_name=request.form['last_name'], email=request.form.get('email',''), phone=request.form.get('phone',''), birth_date=parse_date(request.form.get('birth_date')), preferences=request.form.get('preferences',''), allergies=request.form.get('allergies',''), contraindications=request.form.get('contraindications',''), loyalty_points=int(request.form.get('loyalty_points') or 0))
        db.session.add(customer)
        db.session.commit()
        return redirect(url_for('customers.index'))
    query = request.args.get('q','').strip()
    customers = Customer.query
    if query:
        like = '%' + query + '%'
        customers = customers.filter(db.or_(Customer.first_name.ilike(like), Customer.last_name.ilike(like), Customer.email.ilike(like), Customer.phone.ilike(like)))
    return render_template('customers/index.html', customers=customers.order_by(Customer.created_at.desc()).all(), query=query)

@customers_bp.route('/<int:customer_id>')
@login_required
def detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    appointments = Appointment.query.filter_by(customer_email=customer.email).order_by(Appointment.start_at.desc()).all() if customer.email else []
    return render_template('customers/detail.html', customer=customer, appointments=appointments)
