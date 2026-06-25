from datetime import datetime, date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.extensions import db
from app.models import Appointment, Cabin, SkillILU, Treatment, WorkSlot

booking_bp = Blueprint('booking', __name__)


def _has_overlap(query, start_at, end_at):
    return query.filter(
        Appointment.status == 'confirmed',
        Appointment.start_at < end_at,
        Appointment.end_at > start_at,
    ).first() is not None


def _free_cabin(institute_id, start_at, end_at):
    cabins = Cabin.query.filter_by(institute_id=institute_id, is_active=True).order_by(Cabin.name).all()
    for cabin in cabins:
        busy = _has_overlap(Appointment.query.filter_by(cabin_id=cabin.id), start_at, end_at)
        if not busy:
            return cabin
    return None


def slots_for_treatment(treatment, target_date):
    if target_date < date.today():
        return []

    slots_by_time = {}
    eligible = SkillILU.query.filter(
        SkillILU.treatment_id == treatment.id,
        SkillILU.level.in_(['L', 'U']),
    ).all()

    for skill in eligible:
        work_slots = WorkSlot.query.filter_by(
            user_id=skill.user_id,
            work_date=target_date,
            status='present',
        ).all()

        for ws in work_slots:
            current = datetime.combine(target_date, ws.start_time)
            limit = datetime.combine(target_date, ws.end_time) - timedelta(minutes=treatment.duration_minutes)

            while current <= limit:
                end_at = current + timedelta(minutes=treatment.duration_minutes)
                busy_user = _has_overlap(Appointment.query.filter_by(user_id=skill.user_id), current, end_at)
                cabin = _free_cabin(skill.user.institute_id, current, end_at)

                if not busy_user and cabin:
                    key = current.strftime('%H:%M')
                    slots_by_time.setdefault(key, {
                        'time': key,
                        'user': skill.user,
                        'cabin': cabin,
                        'start_at': current,
                        'end_at': end_at,
                    })

                current += timedelta(minutes=30)

    return [slots_by_time[k] for k in sorted(slots_by_time)]


@booking_bp.route('/')
def choose_treatment():
    treatments = Treatment.query.filter_by(is_active=True).order_by(Treatment.category, Treatment.name).all()
    return render_template('booking/choose_treatment.html', treatments=treatments)


@booking_bp.route('/<int:treatment_id>/calendrier')
def month_calendar(treatment_id):
    treatment = Treatment.query.get_or_404(treatment_id)
    today = date.today()
    days = []
    for i in range(31):
        d = today + timedelta(days=i)
        days.append({'date': d, 'available': len(slots_for_treatment(treatment, d)) > 0})
    return render_template('booking/month.html', treatment=treatment, days=days)


@booking_bp.route('/<int:treatment_id>/jour/<day>', methods=['GET', 'POST'])
def day_slots(treatment_id, day):
    treatment = Treatment.query.get_or_404(treatment_id)
    target_date = datetime.strptime(day, '%Y-%m-%d').date()
    slots = slots_for_treatment(treatment, target_date)

    if request.method == 'POST':
        selected_time = request.form['time']
        chosen = next((s for s in slots if s['time'] == selected_time), None)
        if not chosen:
            flash('Ce creneau n est plus disponible.', 'danger')
            return redirect(request.url)

        appointment = Appointment(
            customer_name=request.form['customer_name'],
            customer_email=request.form.get('customer_email', ''),
            treatment=treatment,
            user=chosen['user'],
            cabin=chosen['cabin'],
            start_at=chosen['start_at'],
            end_at=chosen['end_at'],
        )
        db.session.add(appointment)
        db.session.commit()
        return render_template('booking/confirmed.html', appointment=appointment)

    return render_template('booking/day.html', treatment=treatment, target_date=target_date, slots=slots)
