from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash

from app.extensions import db
from app.models import Appointment, Cabin, Treatment, User, WorkSlot
from app.utils.auth import login_required

planning_bp = Blueprint('planning', __name__)


SCHEDULER_START_HOUR = 8
SCHEDULER_END_HOUR = 20
AVAILABLE_STATUS = 'present'
BLOCKING_STATUS_LABELS = {
    'off': 'Repos',
    'holiday': 'Conge',
    'training': 'Formation',
    'absence': 'Absence',
}


def _day_bounds(d):
    start = datetime.combine(d, datetime.min.time())
    return start, start + timedelta(days=1)


def _overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def _slot_bounds(slot):
    return datetime.combine(slot.work_date, slot.start_time), datetime.combine(slot.work_date, slot.end_time)


def _busy_appointment(query, start_at, end_at, exclude_id=None):
    q = query.filter(Appointment.status != 'cancelled', Appointment.start_at < end_at, Appointment.end_at > start_at)
    if exclude_id:
        q = q.filter(Appointment.id != exclude_id)
    return q.first() is not None


def _free_cabin(institute_id, start_at, end_at, exclude_id=None):
    query = Cabin.query.filter_by(is_active=True)
    if institute_id:
        query = query.filter_by(institute_id=institute_id)
    cabins = query.order_by(Cabin.name).all()
    for cabin in cabins:
        busy = _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), start_at, end_at, exclude_id)
        if not busy:
            return cabin
    return None


def _parse_selected_date():
    selected = request.args.get('date')
    try:
        return datetime.strptime(selected, '%Y-%m-%d').date() if selected else date.today()
    except ValueError:
        return date.today()


def _month_matrix(selected_date):
    first_day = selected_date.replace(day=1)
    cursor = first_day - timedelta(days=first_day.weekday())
    weeks = []
    for _ in range(6):
        week = []
        for _ in range(7):
            week_start = cursor - timedelta(days=cursor.weekday())
            week.append({
                'date': cursor,
                'week_start': week_start,
                'outside': cursor.month != selected_date.month,
                'selected': cursor == selected_date,
                'today': cursor == date.today(),
            })
            cursor += timedelta(days=1)
        weeks.append(week)
    return weeks


def _position_block(start_at, end_at, selected_date):
    day_min = datetime.combine(selected_date, time(SCHEDULER_START_HOUR, 0))
    day_max = datetime.combine(selected_date, time(SCHEDULER_END_HOUR, 0))
    start = max(start_at, day_min)
    end = min(end_at, day_max)
    if end <= start:
        return None
    total_minutes = (SCHEDULER_END_HOUR - SCHEDULER_START_HOUR) * 60
    top = ((start - day_min).total_seconds() / 60) / total_minutes * 100
    height = ((end - start).total_seconds() / 60) / total_minutes * 100
    return round(top, 3), round(max(height, 4.5), 3)


def _block(kind, title, subtitle, start_at, end_at, selected_date, appointment=None, slot=None):
    pos = _position_block(start_at, end_at, selected_date)
    if not pos:
        return None
    return {
        'kind': kind,
        'title': title,
        'subtitle': subtitle,
        'time': f"{start_at.strftime('%H:%M')} - {end_at.strftime('%H:%M')}",
        'top': pos[0],
        'height': pos[1],
        'appointment': appointment,
        'slot': slot,
    }


def _time_slots():
    slots = []
    for minutes in range(SCHEDULER_START_HOUR * 60, SCHEDULER_END_HOUR * 60, 30):
        slots.append({'time': f"{minutes // 60:02d}:{minutes % 60:02d}"})
    return slots


def _time_markers():
    total = SCHEDULER_END_HOUR - SCHEDULER_START_HOUR
    return [{'label': f"{h:02d}:00", 'top': round((h - SCHEDULER_START_HOUR) / total * 100, 3)} for h in range(SCHEDULER_START_HOUR, SCHEDULER_END_HOUR + 1)]


def _user_slots_for_day(user_id, work_date):
    return WorkSlot.query.filter_by(user_id=user_id, work_date=work_date).order_by(WorkSlot.start_time).all()


def _user_is_available(user_id, start_at, end_at):
    if end_at <= start_at:
        return False, 'Le rendez-vous doit avoir une duree positive.'
    if start_at.date() != end_at.date():
        return False, 'Le rendez-vous doit rester sur la meme journee.'

    slots = _user_slots_for_day(user_id, start_at.date())
    if not slots:
        return False, 'La praticienne n est pas indiquee presente sur cette journee.'

    for slot in slots:
        slot_start, slot_end = _slot_bounds(slot)
        if slot.status != AVAILABLE_STATUS and _overlaps(start_at, end_at, slot_start, slot_end):
            label = BLOCKING_STATUS_LABELS.get(slot.status, slot.status)
            return False, f'Praticienne indisponible sur ce creneau ({label}).'

    present_intervals = []
    for slot in slots:
        if slot.status == AVAILABLE_STATUS:
            slot_start, slot_end = _slot_bounds(slot)
            if _overlaps(start_at, end_at, slot_start, slot_end):
                present_intervals.append((slot_start, slot_end))

    if not present_intervals:
        return False, 'Le rendez-vous doit etre positionne sur un creneau vert disponible.'

    present_intervals.sort(key=lambda item: item[0])
    cursor = start_at
    for slot_start, slot_end in present_intervals:
        if slot_end <= cursor:
            continue
        if slot_start > cursor:
            break
        cursor = max(cursor, slot_end)
        if cursor >= end_at:
            return True, ''

    return False, 'La duree du rendez-vous depasse le creneau vert disponible.'


def _slot_states_for_user(user_id, selected_date):
    states = {}
    for slot in _time_slots():
        slot_start = datetime.combine(selected_date, datetime.strptime(slot['time'], '%H:%M').time())
        slot_end = slot_start + timedelta(minutes=30)
        available, _ = _user_is_available(user_id, slot_start, slot_end)
        states[slot['time']] = available
    return states


@planning_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        work_date = datetime.strptime(request.form['work_date'], '%Y-%m-%d').date()
        ws = WorkSlot(user_id=int(request.form['user_id']), work_date=work_date, start_time=datetime.strptime(request.form['start_time'], '%H:%M').time(), end_time=datetime.strptime(request.form['end_time'], '%H:%M').time(), status=request.form.get('status', 'present'), note=request.form.get('note', ''))
        db.session.add(ws)
        db.session.commit()
        return redirect(url_for('planning.index', date=work_date.isoformat(), view=request.args.get('view', 'user')))

    selected_date = _parse_selected_date()
    selected_view = request.args.get('view', 'user')
    if selected_view not in ('user', 'cabin'):
        selected_view = 'user'

    start_day, end_day = _day_bounds(selected_date)
    users = User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all()
    cabins = Cabin.query.filter_by(is_active=True).order_by(Cabin.name).all()
    treatments = Treatment.query.filter_by(is_active=True).order_by(Treatment.category, Treatment.name).all()
    slots = WorkSlot.query.filter_by(work_date=selected_date).all()
    appointments = Appointment.query.filter(Appointment.start_at >= start_day, Appointment.start_at < end_day).order_by(Appointment.start_at).all()

    board_resources = []
    if selected_view == 'user':
        for user in users:
            blocks = []
            for slot in slots:
                if slot.user_id != user.id:
                    continue
                start_at = datetime.combine(slot.work_date, slot.start_time)
                end_at = datetime.combine(slot.work_date, slot.end_time)
                if slot.status == AVAILABLE_STATUS:
                    label = 'Disponible'
                    subtitle = slot.note or 'Peut recevoir un client'
                else:
                    label = BLOCKING_STATUS_LABELS.get(slot.status, slot.status)
                    subtitle = slot.note or 'Indisponible'
                block = _block(slot.status, label, subtitle, start_at, end_at, selected_date, slot=slot)
                if block:
                    blocks.append(block)
            for appointment in appointments:
                if appointment.user_id != user.id:
                    continue
                kind = 'completed' if appointment.status == 'completed' else 'cancelled' if appointment.status == 'cancelled' else 'appointment'
                subtitle = f"{appointment.treatment.name} · {appointment.cabin.name}"
                block = _block(kind, appointment.customer_name, subtitle, appointment.start_at, appointment.end_at, selected_date, appointment=appointment)
                if block:
                    blocks.append(block)
            blocks.sort(key=lambda item: (item['top'], 0 if item['kind'] == AVAILABLE_STATUS else 1))
            board_resources.append({'id': user.id, 'type': 'user', 'name': user.full_name, 'subtitle': user.role.label if user.role else 'Praticienne', 'blocks': blocks, 'slot_states': _slot_states_for_user(user.id, selected_date)})
    else:
        for cabin in cabins:
            blocks = []
            for appointment in appointments:
                if appointment.cabin_id != cabin.id:
                    continue
                kind = 'completed' if appointment.status == 'completed' else 'cancelled' if appointment.status == 'cancelled' else 'appointment cabin-appointment'
                subtitle = f"{appointment.treatment.name} · {appointment.user.full_name}"
                block = _block(kind, appointment.customer_name, subtitle, appointment.start_at, appointment.end_at, selected_date, appointment=appointment)
                if block:
                    blocks.append(block)
            blocks.sort(key=lambda item: item['top'])
            board_resources.append({'id': cabin.id, 'type': 'cabin', 'name': cabin.name, 'subtitle': cabin.cabin_type, 'blocks': blocks, 'slot_states': {slot['time']: True for slot in _time_slots()}})

    return render_template('planning/pro.html', users=users, cabins=cabins, treatments=treatments, slots=slots, appointments=appointments, selected_date=selected_date, prev_day=selected_date - timedelta(days=1), next_day=selected_date + timedelta(days=1), month_weeks=_month_matrix(selected_date), selected_view=selected_view, board_resources=board_resources, time_slots=_time_slots(), time_markers=_time_markers(), scheduler_start_hour=SCHEDULER_START_HOUR, scheduler_end_hour=SCHEDULER_END_HOUR)


@planning_bp.route('/appointment/create', methods=['POST'])
@login_required
def create_appointment():
    treatment = Treatment.query.get_or_404(int(request.form['treatment_id']))
    user = User.query.get_or_404(int(request.form['user_id']))
    cabin = Cabin.query.get_or_404(int(request.form['cabin_id']))
    selected_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
    start_time = datetime.strptime(request.form['time'], '%H:%M').time()
    start_at = datetime.combine(selected_date, start_time)
    end_at = start_at + timedelta(minutes=treatment.duration_minutes or 60)

    if user.institute_id and cabin.institute_id and user.institute_id != cabin.institute_id:
        flash('La cabine selectionnee ne correspond pas a l etablissement de la praticienne.')
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))

    available, message = _user_is_available(user.id, start_at, end_at)
    if not available:
        flash(message)
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))

    if _busy_appointment(Appointment.query.filter_by(user_id=user.id), start_at, end_at):
        flash('Conflit : cette praticienne a deja un rendez-vous sur ce creneau.')
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))
    if _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), start_at, end_at):
        flash('Conflit : cette cabine est deja occupee sur ce creneau.')
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))

    appointment = Appointment(customer_name=request.form['customer_name'], customer_email=request.form.get('customer_email', ''), treatment_id=treatment.id, user_id=user.id, cabin_id=cabin.id, start_at=start_at, end_at=end_at, status='confirmed')
    db.session.add(appointment)
    db.session.commit()
    flash('Rendez-vous cree depuis le planning.')
    return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))


@planning_bp.route('/api/move', methods=['POST'])
@login_required
def move_event():
    data = request.get_json() or {}
    try:
        event_type = data.get('event_type')
        event_id = int(data.get('event_id'))
        resource_type = data.get('resource_type')
        resource_id = int(data.get('resource_id'))
        target_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
        target_time_value = data.get('time') or f"{int(data.get('hour')):02d}:00"
        target_time = datetime.strptime(target_time_value, '%H:%M').time()
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'message': 'Donnees de deplacement invalides'}), 400

    target_start = datetime.combine(target_date, target_time)

    if event_type == 'appointment':
        appointment = Appointment.query.get_or_404(event_id)
        duration = appointment.end_at - appointment.start_at
        target_end = target_start + duration
        if resource_type == 'user':
            user = User.query.get_or_404(resource_id)
            available, message = _user_is_available(user.id, target_start, target_end)
            if not available:
                return jsonify({'ok': False, 'message': message}), 409
            if _busy_appointment(Appointment.query.filter_by(user_id=user.id), target_start, target_end, appointment.id):
                return jsonify({'ok': False, 'message': 'Praticienne deja occupee'}), 409
            if appointment.cabin and not _busy_appointment(Appointment.query.filter_by(cabin_id=appointment.cabin_id), target_start, target_end, appointment.id):
                cabin = appointment.cabin
            else:
                cabin = _free_cabin(user.institute_id, target_start, target_end, appointment.id)
            if not cabin:
                return jsonify({'ok': False, 'message': 'Aucune cabine libre'}), 409
            appointment.user_id = user.id
            appointment.cabin_id = cabin.id
        elif resource_type == 'cabin':
            cabin = Cabin.query.get_or_404(resource_id)
            available, message = _user_is_available(appointment.user_id, target_start, target_end)
            if not available:
                return jsonify({'ok': False, 'message': message}), 409
            if _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), target_start, target_end, appointment.id):
                return jsonify({'ok': False, 'message': 'Cabine deja occupee'}), 409
            if _busy_appointment(Appointment.query.filter_by(user_id=appointment.user_id), target_start, target_end, appointment.id):
                return jsonify({'ok': False, 'message': 'Praticienne deja occupee'}), 409
            appointment.cabin_id = cabin.id
        else:
            return jsonify({'ok': False, 'message': 'Ressource invalide'}), 400
        appointment.start_at = target_start
        appointment.end_at = target_end
        db.session.commit()
        return jsonify({'ok': True})

    if event_type == 'slot' and resource_type == 'user':
        slot = WorkSlot.query.get_or_404(event_id)
        duration = datetime.combine(slot.work_date, slot.end_time) - datetime.combine(slot.work_date, slot.start_time)
        new_end = target_start + duration
        if new_end.date() != target_date:
            return jsonify({'ok': False, 'message': 'Le creneau de presence doit rester sur la meme journee'}), 409
        slot.user_id = resource_id
        slot.work_date = target_date
        slot.start_time = target_start.time()
        slot.end_time = new_end.time()
        db.session.commit()
        return jsonify({'ok': True})

    return jsonify({'ok': False, 'message': 'Mouvement impossible'}), 400