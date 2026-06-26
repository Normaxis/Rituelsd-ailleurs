from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Appointment, StockMovement, TreatmentConsumption
from app.utils.auth import login_required

appointments_bp = Blueprint('appointments', __name__)


def _deduct_stock_for_appointment(appointment):
    consumptions = TreatmentConsumption.query.filter_by(treatment_id=appointment.treatment_id).all()
    for item in consumptions:
        product = item.product
        qty = abs(item.quantity or 0)
        product.quantity = (product.quantity or 0) - qty
        db.session.add(StockMovement(product_id=product.id, movement_type='treatment', quantity=-qty, unit_cost=0, reason='RDV ' + str(appointment.id) + ' - ' + appointment.treatment.name))


@appointments_bp.route('/')
@login_required
def index():
    selected = request.args.get('date')
    selected_date = datetime.strptime(selected, '%Y-%m-%d').date() if selected else date.today()
    start = datetime.combine(selected_date, datetime.min.time())
    end = start + timedelta(days=1)
    appointments = Appointment.query.filter(Appointment.start_at >= start, Appointment.start_at < end).order_by(Appointment.start_at).all()
    return render_template('appointments/index.html', appointments=appointments, selected_date=selected_date, prev_day=selected_date - timedelta(days=1), next_day=selected_date + timedelta(days=1))


@appointments_bp.route('/<int:appointment_id>/realiser', methods=['POST'])
@login_required
def complete(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.status != 'completed':
        _deduct_stock_for_appointment(appointment)
        appointment.status = 'completed'
        db.session.commit()
        flash('Rendez-vous realise et stock deduit.', 'success')
    return redirect(url_for('appointments.index', date=appointment.start_at.date().isoformat()))


@appointments_bp.route('/<int:appointment_id>/annuler', methods=['POST'])
@login_required
def cancel(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'cancelled'
    db.session.commit()
    flash('Rendez-vous annule.', 'success')
    return redirect(url_for('appointments.index', date=appointment.start_at.date().isoformat()))
