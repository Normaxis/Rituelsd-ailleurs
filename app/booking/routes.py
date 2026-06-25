from datetime import datetime, date, time, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Treatment, SkillILU, WorkSlot, Appointment, Cabin

booking_bp = Blueprint('booking', __name__)


def slots_for_treatment(treatment, target_date):
    results = []
    eligible = SkillILU.query.filter(SkillILU.treatment_id == treatment.id, SkillILU.level.in_(['L','U'])).all()
    for skill in eligible:
        for ws in WorkSlot.query.filter_by(user_id=skill.user_id, work_date=target_date, status='present').all():
            current = datetime.combine(target_date, ws.start_time)
            end_limit = datetime.combine(target_date, ws.end_time) - timedelta(minutes=treatment.duration_minutes)
            while current <= end_limit:
                end_at = current + timedelta(minutes=treatment.duration_minutes)
                busy_user = Appointment.query.filter(Appointment.user_id == skill.user_id, Appointment.status=='confirmed', Appointment.start_at < end_at, Appointment.end_at > current).first()
                cabin = Cabin.query.filter_by(institute_id=skill.user.institute_id, is_active=True).first()
                busy_cabin = Appointment.query.filter(Appointment.cabin_id == cabin.id, Appointment.status=='confirmed', Appointment.start_at < end_at, Appointment.end_at > current).first() if cabin else True
                if not busy_user and not busy_cabin and cabin:
                    results.append({'time': current.strftime('%H:%M'), 'user': skill.user, 'cabin': cabin})
                current += timedelta(minutes=30)
    return results

@booking_bp.route('/')
def choose_treatment():
    return render_template('booking/choose_treatment.html', treatments=Treatment.query.filter_by(is_active=True).all())

@booking_bp.route('/<int:treatment_id>/calendrier')
def month_calendar(treatment_id):
    treatment = Treatment.query.get_or_404(treatment_id)
    today = date.today()
    days = []
    for i in range(31):
        d = today + timedelta(days=i)
        available = len(slots_for_treatment(treatment, d)) > 0
        days.append({'date': d, 'available': available})
    return render_template('booking/month.html', treatment=treatment, days=days)

@booking_bp.route('/<int:treatment_id>/jour/<day>', methods=['GET','POST'])
def day_slots(treatment_id, day):
    treatment = Treatment.query.get_or_404(treatment_id)
    target_date = datetime.strptime(day, '%Y-%m-%d').date()
    slots = slots_for_treatment(treatment, target_date)
    if request.method == 'POST':
        selected_time = request.form['time']
        chosen = next((s for s in slots if s['time'] == selected_time), None)
        if not chosen:
            flash('Ce créneau n’est plus disponible.', 'danger')
            return redirect(request.url)
        start_at = datetime.combine(target_date, datetime.strptime(selected_time, '%H:%M').time())
        appointment = Appointment(customer_name=request.form['customer_name'], customer_email=request.form.get('customer_email',''), treatment=treatment, user=chosen['user'], cabin=chosen['cabin'], start_at=start_at, end_at=start_at+timedelta(minutes=treatment.duration_minutes))
        db.session.add(appointment); db.session.commit()
        return render_template('booking/confirmed.html', appointment=appointment)
    return render_template('booking/day.html', treatment=treatment, target_date=target_date, slots=slots)
