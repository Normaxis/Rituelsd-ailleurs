from datetime import datetime
from uuid import uuid4
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Customer, GiftCard, Treatment
from app.utils.auth import login_required

giftcards_bp = Blueprint('giftcards', __name__)

def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None

def make_code():
    return 'KDO-' + uuid4().hex[:10].upper()

@giftcards_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        card = GiftCard(
            code=request.form.get('code') or make_code(),
            customer_id=int(request.form['customer_id']) if request.form.get('customer_id') else None,
            treatment_id=int(request.form['treatment_id']) if request.form.get('treatment_id') else None,
            amount=float(request.form.get('amount') or 0),
            label=request.form.get('label',''),
            expires_on=parse_date(request.form.get('expires_on')),
            status=request.form.get('status','active'),
        )
        db.session.add(card)
        db.session.commit()
        return redirect(url_for('giftcards.index'))
    cards = GiftCard.query.order_by(GiftCard.created_at.desc()).all()
    customers = Customer.query.order_by(Customer.first_name, Customer.last_name).all()
    treatments = Treatment.query.filter_by(is_active=True).order_by(Treatment.name).all()
    return render_template('giftcards/index.html', cards=cards, customers=customers, treatments=treatments)

@giftcards_bp.route('/<int:card_id>')
@login_required
def detail(card_id):
    card = GiftCard.query.get_or_404(card_id)
    return render_template('giftcards/detail.html', card=card)
