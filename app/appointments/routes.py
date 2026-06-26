from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Appointment, Cabin, StockMovement, Treatment, TreatmentConsumption, User, WaitlistEntry
from app.utils.auth import login_required

appointments_bp = Blueprint('appointments', __name__)


def _deduct_stock_for_appointment(appointment):
    consumptions = TreatmentConsumption.query.filter_by(treatment_id=appointment.treatment_id).all()
    for item in consumptions:
        product = item.product
        qty = abs(item.quantity or 0)
        product.quantity = (product.quantity or 0) - qty
        db.session.add(StockMovement(product_id=product.id, movement_type='treatment', quantity=-qty, unit_cost=0, reason='RDV ' + str(appointment.id) + ' - ' + appointment.treatment.name))


def _has_conflict(user_id, cabin_id, start_at, end_at):
    base = Appointment.query.filter(Appointment.status != 'cancelled', Appointment.start_at < end_at, Appointment.end_at > start_at)
    user_busy = base.filter(Appointment.user_id == user_id).first() is not None
    cabin_busy = base.filter(Appointment.cabin_id == cabin_id).first() is not None
    return user_busy or cabin_busy


@appointments_bp.route('/')
@login_required
def index():
    selected = request.args.get('date')
    selected_date = datetime.strptime(selected, '%Y-%m-%d').date() if selected else date.today()
    start = datetime.combine(selected_date, datetime.min.time())
    end = start + timedelta(days=1)
    appointments = Appointment.query.filter(Appointment.start_at >= start, Appointment.start_at < end).order_by(Appointment.start_at).all()
    return render_template('appointments/index.html', appointments=appointments, selected_date=selected_date, prev_day=selected_date - timedelta(days=1), next_day=selected_date + timedelta(days=1))


@appointments_bp.route('/nouveau', methods=['GET','POST'])
@login_required
def create():
    waitlist_id = request.form.get('waitlist_id') or request.args.get('waitlist_id')
    waitlist_entry = WaitlistEntry.query.get(int(waitlist_id)) if waitlist_id else None

    if request.method == 'POST':
        treatment = Treatment.query.get_or_404(int(request.form['treatment_id']))
        user_id = int(request.form['user_id'])
        cabin_id = int(request.form['cabin_id'])
        start_at = datetime.strptime(request.form['date'] + ' ' + request.form['time'], '%Y-%m-%d %H:%M')
        end_at = start_at + timedelta(minutes=treatment.duration_minutes)
        if _has_conflict(user_id, cabin_id, start_at, end_at):
            flash('Conflit detecte sur la praticienne ou la cabine.', 'danger')
            target = url_for('appointments.create', waitlist_id=waitlist_entry.id) if waitlist_entry else url_for('appointments.create')
            return redirect(target)
        appt = Appointment(customer_name=request.form['customer_name'], customer_email=request.form.get('customer_email',''), treatment_id=treatment.id, user_id=user_id, cabin_id=cabin_id, start_at=start_at, end_at=end_at, status='confirmed')
        db.session.add(appt)
        if waitlist_entry:
            waitlist_entry.status = 'converted'
        db.session.commit()
        flash('Rendez-vous cree.', 'success')
        return redirect(url_for('appointments.index', date=start_at.date().isoformat()))

    return render_template('appointments/form.html', treatments=Treatment.query.filter_by(is_active=True).order_by(Treatment.name).all(), users=User.query.filter_by(is_active=True).order_by(User.last_name, User.first_name).all(), cabins=Cabin.query.filter_by(is_active=True).order_by(Cabin.name).all(), today=date.today(), waitlist_entry=waitlist_entry)


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
