from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify, render_template, request, redirect, url_for

from app.extensions import db
from app.models import Appointment, Cabin, User, WorkSlot
from app.utils.auth import login_required

planning_bp = Blueprint('planning', __name__)


def _day_bounds(d):
    start = datetime.combine(d, datetime.min.time())
    return start, start + timedelta(days=1)


def _busy_appointment(query, start_at, end_at, exclude_id=None):
    q = query.filter(Appointment.status == 'confirmed', Appointment.start_at < end_at, Appointment.end_at > start_at)
    if exclude_id:
        q = q.filter(Appointment.id != exclude_id)
    return q.first() is not None


def _free_cabin(institute_id, start_at, end_at, exclude_id=None):
    cabins = Cabin.query.filter_by(institute_id=institute_id, is_active=True).order_by(Cabin.name).all()
    for cabin in cabins:
        busy = _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), start_at, end_at, exclude_id)
        if not busy:
            return cabin
    return None


@planning_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        work_date = datetime.strptime(request.form['work_date'], '%Y-%m-%d').date()
        ws = WorkSlot(user_id=int(request.form['user_id']), work_date=work_date, start_time=datetime.strptime(request.form['start_time'], '%H:%M').time(), end_time=datetime.strptime(request.form['end_time'], '%H:%M').time(), status=request.form.get('status', 'present'), note=request.form.get('note', ''))
        db.session.add(ws)
        db.session.commit()
        return redirect(url_for('planning.index', date=work_date.isoformat()))

    selected = request.args.get('date')
    selected_date = datetime.strptime(selected, '%Y-%m-%d').date() if selected else date.today()
    start_day, end_day = _day_bounds(selected_date)
    users = User.query.order_by(User.first_name, User.last_name).all()
    cabins = Cabin.query.filter_by(is_active=True).order_by(Cabin.name).all()
    slots = WorkSlot.query.filter_by(work_date=selected_date).all()
    appointments = Appointment.query.filter(Appointment.start_at >= start_day, Appointment.start_at < end_day).order_by(Appointment.start_at).all()
    hours = list(range(8, 21))
    return render_template('planning/pro.html', users=users, cabins=cabins, slots=slots, appointments=appointments, selected_date=selected_date, prev_day=selected_date - timedelta(days=1), next_day=selected_date + timedelta(days=1), hours=hours)


@planning_bp.route('/api/move', methods=['POST'])
@login_required
def move_event():
    data = request.get_json() or {}
    event_type = data.get('event_type')
    event_id = int(data.get('event_id'))
    resource_type = data.get('resource_type')
    resource_id = int(data.get('resource_id'))
    target_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
    target_hour = int(data.get('hour'))
    target_start = datetime.combine(target_date, time(target_hour, 0))

    if event_type == 'appointment':
        appointment = Appointment.query.get_or_404(event_id)
        duration = appointment.end_at - appointment.start_at
        target_end = target_start + duration
        if resource_type == 'user':
            user = User.query.get_or_404(resource_id)
            if _busy_appointment(Appointment.query.filter_by(user_id=user.id), target_start, target_end, appointment.id):
                return jsonify({'ok': False, 'message': 'Praticienne deja occupee'}), 409
            cabin = _free_cabin(user.institute_id, target_start, target_end, appointment.id)
            if not cabin:
                return jsonify({'ok': False, 'message': 'Aucune cabine libre'}), 409
            appointment.user_id = user.id
            appointment.cabin_id = cabin.id
        elif resource_type == 'cabin':
            cabin = Cabin.query.get_or_404(resource_id)
            if _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), target_start, target_end, appointment.id):
                return jsonify({'ok': False, 'message': 'Cabine deja occupee'}), 409
            appointment.cabin_id = cabin.id
        appointment.start_at = target_start
        appointment.end_at = target_end
        db.session.commit()
        return jsonify({'ok': True})

    if event_type == 'slot' and resource_type == 'user':
        slot = WorkSlot.query.get_or_404(event_id)
        duration = datetime.combine(slot.work_date, slot.end_time) - datetime.combine(slot.work_date, slot.start_time)
        new_end = target_start + duration
        slot.user_id = resource_id
        slot.work_date = target_date
        slot.start_time = target_start.time()
        slot.end_time = new_end.time()
        db.session.commit()
        return jsonify({'ok': True})

    return jsonify({'ok': False, 'message': 'Mouvement impossible'}), 400
