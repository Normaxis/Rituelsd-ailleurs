from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Treatment, WaitlistEntry
from app.utils.auth import login_required

waitlist_bp = Blueprint('waitlist', __name__)

STATUSES = ['open', 'contacted', 'converted', 'closed']

def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').date()

@waitlist_bp.route('/reservation/attente', methods=['POST'])
def create():
    treatment = Treatment.query.get_or_404(int(request.form['treatment_id']))
    entry = WaitlistEntry(treatment=treatment, customer_name=request.form['customer_name'], customer_email=request.form.get('customer_email',''), customer_phone=request.form.get('customer_phone',''), preferred_date=parse_date(request.form.get('preferred_date')), preferred_period=request.form.get('preferred_period',''), practitioner_name=request.form.get('practitioner_name',''), note=request.form.get('note',''))
    db.session.add(entry)
    db.session.commit()
    return render_template('booking/waitlist_confirmed.html', entry=entry)

@waitlist_bp.route('/admin/attente')
@login_required
def admin_index():
    selected_status = request.args.get('status','')
    query = WaitlistEntry.query
    if selected_status:
        query = query.filter_by(status=selected_status)
    entries = query.order_by(WaitlistEntry.created_at.desc()).all()
    counts = {status: WaitlistEntry.query.filter_by(status=status).count() for status in STATUSES}
    return render_template('waitlist/index.html', entries=entries, statuses=STATUSES, counts=counts, selected_status=selected_status)

@waitlist_bp.route('/admin/attente/<int:entry_id>/statut', methods=['POST'])
@login_required
def update_status(entry_id):
    entry = WaitlistEntry.query.get_or_404(entry_id)
    status = request.form.get('status','open')
    if status in STATUSES:
        entry.status = status
        db.session.commit()
    return redirect(url_for('waitlist.admin_index'))
