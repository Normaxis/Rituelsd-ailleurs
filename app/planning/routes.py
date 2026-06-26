from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash

from app.extensions import db
from app.models import Appointment, Cabin, CabinAvailabilitySlot, Treatment, User, WeeklyCabinSchedule, WeeklyUserSchedule, WorkSlot
from app.utils.auth import login_required

planning_bp = Blueprint('planning', __name__)

SCHEDULER_START_HOUR = 8
SCHEDULER_END_HOUR = 20
AVAILABLE_STATUS = 'present'
CABIN_AVAILABLE_STATUS = 'available'
WEEKDAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
BLOCKING_STATUS_LABELS = {'off': 'Repos', 'holiday': 'Congé', 'training': 'Formation', 'absence': 'Absence'}
CABIN_STATUS_LABELS = {'available': 'Cabine disponible', 'closed': 'Cabine fermée', 'maintenance': 'Maintenance'}


def _day_bounds(d):
    start = datetime.combine(d, datetime.min.time())
    return start, start + timedelta(days=1)


def _week_start(d):
    return d - timedelta(days=d.weekday())


def _date_label_fr(d):
    return f"{WEEKDAYS[d.weekday()]} {d.day:02d} {MONTHS[d.month - 1]} {d.year}"


def _month_label_fr(d):
    return f"{MONTHS[d.month - 1].capitalize()} {d.year}"


def _overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def _slot_bounds(slot):
    return datetime.combine(slot.work_date, slot.start_time), datetime.combine(slot.work_date, slot.end_time)


def _busy_appointment(query, start_at, end_at, exclude_id=None):
    q = query.filter(Appointment.status != 'cancelled', Appointment.start_at < end_at, Appointment.end_at > start_at)
    if exclude_id:
        q = q.filter(Appointment.id != exclude_id)
    return q.first() is not None


def _intervals_cover(start_at, end_at, intervals):
    intervals = sorted(intervals, key=lambda item: item[0])
    cursor = start_at
    for interval_start, interval_end in intervals:
        if interval_end <= cursor:
            continue
        if interval_start > cursor:
            break
        cursor = max(cursor, interval_end)
        if cursor >= end_at:
            return True
    return False


def _cabin_is_available(cabin_id, start_at, end_at):
    slots = CabinAvailabilitySlot.query.filter_by(cabin_id=cabin_id, work_date=start_at.date()).order_by(CabinAvailabilitySlot.start_time).all()
    if not slots:
        return True, ''
    available_intervals = []
    for slot in slots:
        slot_start, slot_end = _slot_bounds(slot)
        if slot.status != CABIN_AVAILABLE_STATUS and _overlaps(start_at, end_at, slot_start, slot_end):
            return False, f"Cabine indisponible sur ce créneau ({CABIN_STATUS_LABELS.get(slot.status, slot.status)})."
        if slot.status == CABIN_AVAILABLE_STATUS and _overlaps(start_at, end_at, slot_start, slot_end):
            available_intervals.append((slot_start, slot_end))
    if available_intervals and _intervals_cover(start_at, end_at, available_intervals):
        return True, ''
    return False, 'La durée du rendez-vous dépasse la disponibilité de la cabine.'


def _free_cabin(institute_id, start_at, end_at, exclude_id=None):
    query = Cabin.query.filter_by(is_active=True)
    if institute_id:
        query = query.filter_by(institute_id=institute_id)
    cabins = query.order_by(Cabin.name).all()
    for cabin in cabins:
        cabin_available, _ = _cabin_is_available(cabin.id, start_at, end_at)
        busy = _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), start_at, end_at, exclude_id)
        if cabin_available and not busy:
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
            week.append({'date': cursor, 'week_start': week_start, 'outside': cursor.month != selected_date.month, 'selected': cursor == selected_date, 'today': cursor == date.today()})
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


def _block(kind, title, subtitle, start_at, end_at, selected_date, appointment=None, slot=None, cabin_slot=None):
    pos = _position_block(start_at, end_at, selected_date)
    if not pos:
        return None
    return {'kind': kind, 'title': title, 'subtitle': subtitle, 'time': f"{start_at.strftime('%H:%M')} - {end_at.strftime('%H:%M')}", 'top': pos[0], 'height': pos[1], 'appointment': appointment, 'slot': slot, 'cabin_slot': cabin_slot}


def _time_slots():
    return [{'time': f"{minutes // 60:02d}:{minutes % 60:02d}"} for minutes in range(SCHEDULER_START_HOUR * 60, SCHEDULER_END_HOUR * 60, 30)]


def _time_markers():
    total = SCHEDULER_END_HOUR - SCHEDULER_START_HOUR
    return [{'label': f"{h:02d}:00", 'top': round((h - SCHEDULER_START_HOUR) / total * 100, 3)} for h in range(SCHEDULER_START_HOUR, SCHEDULER_END_HOUR + 1)]


def _user_slots_for_day(user_id, work_date):
    return WorkSlot.query.filter_by(user_id=user_id, work_date=work_date).order_by(WorkSlot.start_time).all()


def _user_is_available(user_id, start_at, end_at):
    if end_at <= start_at:
        return False, 'Le rendez-vous doit avoir une durée positive.'
    if start_at.date() != end_at.date():
        return False, 'Le rendez-vous doit rester sur la même journée.'
    slots = _user_slots_for_day(user_id, start_at.date())
    if not slots:
        return False, 'La praticienne n’est pas indiquée présente sur cette journée.'
    for slot in slots:
        slot_start, slot_end = _slot_bounds(slot)
        if slot.status != AVAILABLE_STATUS and _overlaps(start_at, end_at, slot_start, slot_end):
            return False, f"Praticienne indisponible sur ce créneau ({BLOCKING_STATUS_LABELS.get(slot.status, slot.status)})."
    present_intervals = []
    for slot in slots:
        if slot.status == AVAILABLE_STATUS:
            slot_start, slot_end = _slot_bounds(slot)
            if _overlaps(start_at, end_at, slot_start, slot_end):
                present_intervals.append((slot_start, slot_end))
    if not present_intervals:
        return False, 'Le rendez-vous doit être positionné sur un créneau vert disponible.'
    if _intervals_cover(start_at, end_at, present_intervals):
        return True, ''
    return False, 'La durée du rendez-vous dépasse le créneau vert disponible.'


def _slot_states_for_user(user_id, selected_date):
    states = {}
    for slot in _time_slots():
        slot_start = datetime.combine(selected_date, datetime.strptime(slot['time'], '%H:%M').time())
        slot_end = slot_start + timedelta(minutes=30)
        available, _ = _user_is_available(user_id, slot_start, slot_end)
        states[slot['time']] = available
    return states


def _parse_week_start(value):
    try:
        return _week_start(datetime.strptime(value, '%Y-%m-%d').date())
    except (TypeError, ValueError):
        return _week_start(date.today())


def _parse_week_count():
    try:
        return max(1, min(12, int(request.form.get('week_count', 1))))
    except (TypeError, ValueError):
        return 1


def _create_work_slot_from_base(base, target_date):
    return WorkSlot(user_id=base.user_id, work_date=target_date, start_time=base.start_time, end_time=base.end_time, status=base.status, note=base.note or 'Horaire de base')


def _create_cabin_slot_from_base(base, target_date):
    return CabinAvailabilitySlot(cabin_id=base.cabin_id, work_date=target_date, start_time=base.start_time, end_time=base.end_time, status=base.status, note=base.note or 'Disponibilité de base')


def _base_user_schedule_map():
    mapped = {}
    for slot in WeeklyUserSchedule.query.order_by(WeeklyUserSchedule.user_id, WeeklyUserSchedule.weekday).all():
        mapped.setdefault(slot.user_id, {})[slot.weekday] = slot
    return mapped


def _base_cabin_schedule_map():
    mapped = {}
    for slot in WeeklyCabinSchedule.query.order_by(WeeklyCabinSchedule.cabin_id, WeeklyCabinSchedule.weekday).all():
        mapped.setdefault(slot.cabin_id, {})[slot.weekday] = slot
    return mapped


def _week_work_slot_map(week_start):
    week_end = week_start + timedelta(days=7)
    mapped = {}
    slots = WorkSlot.query.filter(WorkSlot.work_date >= week_start, WorkSlot.work_date < week_end).order_by(WorkSlot.user_id, WorkSlot.work_date, WorkSlot.start_time).all()
    for slot in slots:
        mapped.setdefault(slot.user_id, {})[slot.work_date.weekday()] = slot
    return mapped


def _week_cabin_slot_map(week_start):
    week_end = week_start + timedelta(days=7)
    mapped = {}
    slots = CabinAvailabilitySlot.query.filter(CabinAvailabilitySlot.work_date >= week_start, CabinAvailabilitySlot.work_date < week_end).order_by(CabinAvailabilitySlot.cabin_id, CabinAvailabilitySlot.work_date, CabinAvailabilitySlot.start_time).all()
    for slot in slots:
        mapped.setdefault(slot.cabin_id, {})[slot.work_date.weekday()] = slot
    return mapped


def _week_days(week_start):
    return [{'date': week_start + timedelta(days=i), 'label': WEEKDAYS[i]} for i in range(7)]


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
    selected_week_start = _week_start(selected_date)
    week_days = _week_days(selected_week_start)

    start_day, end_day = _day_bounds(selected_date)
    users = User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all()
    cabins = Cabin.query.filter_by(is_active=True).order_by(Cabin.name).all()
    treatments = Treatment.query.filter_by(is_active=True).order_by(Treatment.category, Treatment.name).all()
    slots = WorkSlot.query.filter_by(work_date=selected_date).all()
    cabin_slots = CabinAvailabilitySlot.query.filter_by(work_date=selected_date).all()
    appointments = Appointment.query.filter(Appointment.start_at >= start_day, Appointment.start_at < end_day).order_by(Appointment.start_at).all()

    board_resources = []
    if selected_view == 'user':
        for user in users:
            blocks = []
            for slot in slots:
                if slot.user_id != user.id:
                    continue
                start_at, end_at = _slot_bounds(slot)
                label = 'Disponible' if slot.status == AVAILABLE_STATUS else BLOCKING_STATUS_LABELS.get(slot.status, slot.status)
                subtitle = slot.note or ('Peut recevoir un client' if slot.status == AVAILABLE_STATUS else 'Indisponible')
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
            for cabin_slot in cabin_slots:
                if cabin_slot.cabin_id != cabin.id:
                    continue
                start_at, end_at = _slot_bounds(cabin_slot)
                kind = 'cabin-available' if cabin_slot.status == CABIN_AVAILABLE_STATUS else 'cabin-closed'
                block = _block(kind, CABIN_STATUS_LABELS.get(cabin_slot.status, cabin_slot.status), cabin_slot.note or cabin.cabin_type, start_at, end_at, selected_date, cabin_slot=cabin_slot)
                if block:
                    blocks.append(block)
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

    return render_template('planning/pro.html', users=users, cabins=cabins, treatments=treatments, slots=slots, appointments=appointments, selected_date=selected_date, selected_date_label=_date_label_fr(selected_date), selected_month_label=_month_label_fr(selected_date), prev_day=selected_date - timedelta(days=1), next_day=selected_date + timedelta(days=1), week_start=selected_week_start, prev_week=selected_week_start - timedelta(days=7), next_week=selected_week_start + timedelta(days=7), week_days=week_days, weekdays=WEEKDAYS, months=MONTHS, month_weeks=_month_matrix(selected_date), selected_view=selected_view, board_resources=board_resources, time_slots=_time_slots(), time_markers=_time_markers(), scheduler_start_hour=SCHEDULER_START_HOUR, scheduler_end_hour=SCHEDULER_END_HOUR, user_base_schedules=WeeklyUserSchedule.query.order_by(WeeklyUserSchedule.user_id, WeeklyUserSchedule.weekday, WeeklyUserSchedule.start_time).all(), cabin_base_schedules=WeeklyCabinSchedule.query.order_by(WeeklyCabinSchedule.cabin_id, WeeklyCabinSchedule.weekday, WeeklyCabinSchedule.start_time).all(), staff_base_slots=_base_user_schedule_map(), cabin_base_slots=_base_cabin_schedule_map(), staff_week_slots=_week_work_slot_map(selected_week_start), cabin_week_slots=_week_cabin_slot_map(selected_week_start))


@planning_bp.route('/weekly-plan', methods=['POST'])
@login_required
def weekly_plan():
    week_start = _parse_week_start(request.form.get('week_start'))
    action = request.form.get('action', 'save_week_table')
    week_count = _parse_week_count()
    period_end = week_start + timedelta(days=7 * week_count)

    if action == 'save_week_table':
        user_ids = [int(value) for value in request.form.getlist('staff_user_id')]
        cabin_ids = [int(value) for value in request.form.getlist('cabin_id')]
        if user_ids:
            WorkSlot.query.filter(WorkSlot.user_id.in_(user_ids), WorkSlot.work_date >= week_start, WorkSlot.work_date < period_end).delete(synchronize_session=False)
        if cabin_ids:
            CabinAvailabilitySlot.query.filter(CabinAvailabilitySlot.cabin_id.in_(cabin_ids), CabinAvailabilitySlot.work_date >= week_start, CabinAvailabilitySlot.work_date < period_end).delete(synchronize_session=False)
        try:
            for week_offset in range(week_count):
                target_week = week_start + timedelta(days=7 * week_offset)
                for user_id in user_ids:
                    for weekday in range(7):
                        if not request.form.get(f'staff_active_{user_id}_{weekday}'):
                            continue
                        start_time = datetime.strptime(request.form[f'staff_start_{user_id}_{weekday}'], '%H:%M').time()
                        end_time = datetime.strptime(request.form[f'staff_end_{user_id}_{weekday}'], '%H:%M').time()
                        if end_time <= start_time:
                            raise ValueError('Horaire praticienne invalide')
                        db.session.add(WorkSlot(user_id=user_id, work_date=target_week + timedelta(days=weekday), start_time=start_time, end_time=end_time, status=request.form.get(f'staff_status_{user_id}_{weekday}', AVAILABLE_STATUS), note=request.form.get(f'staff_note_{user_id}_{weekday}', '')))
                for cabin_id in cabin_ids:
                    for weekday in range(7):
                        if not request.form.get(f'cabin_active_{cabin_id}_{weekday}'):
                            continue
                        start_time = datetime.strptime(request.form[f'cabin_start_{cabin_id}_{weekday}'], '%H:%M').time()
                        end_time = datetime.strptime(request.form[f'cabin_end_{cabin_id}_{weekday}'], '%H:%M').time()
                        if end_time <= start_time:
                            raise ValueError('Horaire cabine invalide')
                        db.session.add(CabinAvailabilitySlot(cabin_id=cabin_id, work_date=target_week + timedelta(days=weekday), start_time=start_time, end_time=end_time, status=request.form.get(f'cabin_status_{cabin_id}_{weekday}', CABIN_AVAILABLE_STATUS), note=request.form.get(f'cabin_note_{cabin_id}_{weekday}', '')))
        except (KeyError, ValueError):
            db.session.rollback()
            flash('Un horaire de la semaine est invalide.', 'error')
            return redirect(url_for('planning.index', date=week_start.isoformat(), view=request.form.get('view', 'user')))
        db.session.commit()
        flash(f'Planification enregistrée sur {week_count} semaine(s).', 'success')
        return redirect(url_for('planning.index', date=week_start.isoformat(), view=request.form.get('view', 'user')))

    if action == 'generate_base':
        WorkSlot.query.filter(WorkSlot.work_date >= week_start, WorkSlot.work_date < period_end).delete(synchronize_session=False)
        CabinAvailabilitySlot.query.filter(CabinAvailabilitySlot.work_date >= week_start, CabinAvailabilitySlot.work_date < period_end).delete(synchronize_session=False)
        for week_offset in range(week_count):
            target_week = week_start + timedelta(days=7 * week_offset)
            for base in WeeklyUserSchedule.query.all():
                db.session.add(_create_work_slot_from_base(base, target_week + timedelta(days=base.weekday)))
            for base in WeeklyCabinSchedule.query.all():
                db.session.add(_create_cabin_slot_from_base(base, target_week + timedelta(days=base.weekday)))
        db.session.commit()
        flash(f'Semaine générée depuis les horaires de base sur {week_count} semaine(s).', 'success')
        return redirect(url_for('planning.index', date=week_start.isoformat(), view=request.form.get('view', 'user')))

    work_date = datetime.strptime(request.form['work_date'], '%Y-%m-%d').date()
    start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
    end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
    if end_time <= start_time:
        flash('Horaire invalide.', 'error')
        return redirect(url_for('planning.index', date=work_date.isoformat(), view=request.form.get('view', 'user')))
    if request.form.get('resource_type') == 'cabin':
        db.session.add(CabinAvailabilitySlot(cabin_id=int(request.form['cabin_id']), work_date=work_date, start_time=start_time, end_time=end_time, status=request.form.get('cabin_status', CABIN_AVAILABLE_STATUS), note=request.form.get('note', '')))
    else:
        db.session.add(WorkSlot(user_id=int(request.form['user_id']), work_date=work_date, start_time=start_time, end_time=end_time, status=request.form.get('user_status', AVAILABLE_STATUS), note=request.form.get('note', '')))
    db.session.commit()
    flash('Créneau ajouté à la semaine.', 'success')
    return redirect(url_for('planning.index', date=work_date.isoformat(), view=request.form.get('view', 'user')))


@planning_bp.route('/week-print')
@login_required
def week_print():
    week_start = _parse_week_start(request.args.get('date'))
    week_end = week_start + timedelta(days=7)
    users = User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all()
    cabins = Cabin.query.filter_by(is_active=True).order_by(Cabin.name).all()
    appointments = Appointment.query.filter(Appointment.start_at >= week_start, Appointment.start_at < week_end).order_by(Appointment.start_at).all()
    appointments_by_day = {i: [] for i in range(7)}
    for appointment in appointments:
        appointments_by_day[appointment.start_at.date().weekday()].append(appointment)
    return render_template('planning/week_print.html', week_start=week_start, week_days=_week_days(week_start), week_label=f"{_date_label_fr(week_start)} - {_date_label_fr(week_end - timedelta(days=1))}", users=users, cabins=cabins, staff_week_slots=_week_work_slot_map(week_start), cabin_week_slots=_week_cabin_slot_map(week_start), appointments_by_day=appointments_by_day, weekdays=WEEKDAYS)


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
        flash('La cabine sélectionnée ne correspond pas à l’établissement de la praticienne.')
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))
    available, message = _user_is_available(user.id, start_at, end_at)
    if not available:
        flash(message)
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))
    cabin_available, cabin_message = _cabin_is_available(cabin.id, start_at, end_at)
    if not cabin_available:
        flash(cabin_message)
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))
    if _busy_appointment(Appointment.query.filter_by(user_id=user.id), start_at, end_at):
        flash('Conflit : cette praticienne a déjà un rendez-vous sur ce créneau.')
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))
    if _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), start_at, end_at):
        flash('Conflit : cette cabine est déjà occupée sur ce créneau.')
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=request.form.get('view', 'user')))

    appointment = Appointment(customer_name=request.form['customer_name'], customer_email=request.form.get('customer_email', ''), treatment_id=treatment.id, user_id=user.id, cabin_id=cabin.id, start_at=start_at, end_at=end_at, status='confirmed')
    db.session.add(appointment)
    db.session.commit()
    flash('Rendez-vous créé depuis le planning.')
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
        return jsonify({'ok': False, 'message': 'Données de déplacement invalides'}), 400
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
                return jsonify({'ok': False, 'message': 'Praticienne déjà occupée'}), 409
            if appointment.cabin and not _busy_appointment(Appointment.query.filter_by(cabin_id=appointment.cabin_id), target_start, target_end, appointment.id):
                cabin_available, _ = _cabin_is_available(appointment.cabin_id, target_start, target_end)
                cabin = appointment.cabin if cabin_available else None
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
            cabin_available, cabin_message = _cabin_is_available(cabin.id, target_start, target_end)
            if not cabin_available:
                return jsonify({'ok': False, 'message': cabin_message}), 409
            if _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), target_start, target_end, appointment.id):
                return jsonify({'ok': False, 'message': 'Cabine déjà occupée'}), 409
            if _busy_appointment(Appointment.query.filter_by(user_id=appointment.user_id), target_start, target_end, appointment.id):
                return jsonify({'ok': False, 'message': 'Praticienne déjà occupée'}), 409
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
            return jsonify({'ok': False, 'message': 'Le créneau doit rester sur la même journée'}), 409
        slot.user_id = resource_id
        slot.work_date = target_date
        slot.start_time = target_start.time()
        slot.end_time = new_end.time()
        db.session.commit()
        return jsonify({'ok': True})

    return jsonify({'ok': False, 'message': 'Mouvement impossible'}), 400