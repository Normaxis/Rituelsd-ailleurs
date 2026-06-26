import secrets
from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session, abort
from sqlalchemy import or_

from app.extensions import db
from app.models import (
    Appointment,
    Cabin,
    CabinAvailabilitySlot,
    SkillILU,
    Treatment,
    TreatmentCabinCompatibility,
    User,
    WeeklyCabinSchedule,
    WeeklyUserSchedule,
    WorkSlot,
)
from app.utils.auth import login_required

planning_bp = Blueprint('planning', __name__)

SCHEDULER_START_HOUR = 8
SCHEDULER_END_HOUR = 20
AVAILABLE_STATUS = 'present'
CABIN_AVAILABLE_STATUS = 'available'
PLANNING_MANAGER_ROLES = {'general_admin', 'agency_manager'}
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


def _current_user():
    user_id = session.get('user_id')
    return User.query.get(user_id) if user_id else None


def _can_manage_planning():
    return session.get('role') in PLANNING_MANAGER_ROLES


def _scope_institute_id():
    user = _current_user()
    if not user or session.get('role') == 'general_admin':
        return None
    return user.institute_id


def _entity_in_scope(entity):
    scope_id = _scope_institute_id()
    if scope_id is None:
        return True
    entity_institute_id = getattr(entity, 'institute_id', None)
    return entity_institute_id in (None, scope_id)


def _require_planning_manager_json():
    if _can_manage_planning():
        return None
    return jsonify({'ok': False, 'message': 'Droits insuffisants pour modifier le planning.'}), 403


def _require_planning_manager_form(selected_date=None, view='user'):
    if _can_manage_planning():
        return None
    flash('Droits insuffisants pour modifier le planning.', 'error')
    return redirect(url_for('planning.index', date=(selected_date or date.today()).isoformat(), view=view))


def _planning_csrf_token():
    token = session.get('_planning_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_planning_csrf_token'] = token
    return token


def _valid_planning_csrf():
    expected = session.get('_planning_csrf_token')
    provided = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token') or request.headers.get('X-CSRFToken')
    return bool(expected and provided and secrets.compare_digest(str(expected), str(provided)))


def _csrf_form_guard(selected_date=None, view='user'):
    if _valid_planning_csrf():
        return None
    flash('Session expirée ou formulaire invalide. Merci de réessayer.', 'error')
    return redirect(url_for('planning.index', date=(selected_date or date.today()).isoformat(), view=view))


def _csrf_json_guard():
    if _valid_planning_csrf():
        return None
    return jsonify({'ok': False, 'message': 'Session expirée ou requête invalide.'}), 403


def _cabin_is_available(cabin_id, start_at, end_at):
    slots = CabinAvailabilitySlot.query.filter_by(cabin_id=cabin_id, work_date=start_at.date()).order_by(CabinAvailabilitySlot.start_time).all()
    if not slots:
        return False, 'Aucune disponibilité cabine n’est renseignée sur cette journée.'
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


def _free_cabin(institute_id, start_at, end_at, exclude_id=None, treatment=None):
    query = Cabin.query.filter_by(is_active=True)
    if institute_id:
        query = query.filter_by(institute_id=institute_id)
    cabins = query.order_by(Cabin.name).all()
    for cabin in cabins:
        if not _entity_in_scope(cabin):
            continue
        if treatment and _cabin_compatibility_error(treatment, cabin):
            continue
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
    query = WeeklyUserSchedule.query.order_by(WeeklyUserSchedule.user_id, WeeklyUserSchedule.weekday)
    scope_id = _scope_institute_id()
    if scope_id is not None:
        query = query.join(User, WeeklyUserSchedule.user_id == User.id).filter(User.institute_id == scope_id)
    for slot in query.all():
        mapped.setdefault(slot.user_id, {})[slot.weekday] = slot
    return mapped


def _base_cabin_schedule_map():
    mapped = {}
    query = WeeklyCabinSchedule.query.order_by(WeeklyCabinSchedule.cabin_id, WeeklyCabinSchedule.weekday)
    scope_id = _scope_institute_id()
    if scope_id is not None:
        query = query.join(Cabin, WeeklyCabinSchedule.cabin_id == Cabin.id).filter(Cabin.institute_id == scope_id)
    for slot in query.all():
        mapped.setdefault(slot.cabin_id, {})[slot.weekday] = slot
    return mapped


def _week_work_slot_map(week_start):
    week_end = week_start + timedelta(days=7)
    mapped = {}
    query = WorkSlot.query.filter(WorkSlot.work_date >= week_start, WorkSlot.work_date < week_end).order_by(WorkSlot.user_id, WorkSlot.work_date, WorkSlot.start_time)
    scope_id = _scope_institute_id()
    if scope_id is not None:
        query = query.join(User, WorkSlot.user_id == User.id).filter(User.institute_id == scope_id)
    for slot in query.all():
        mapped.setdefault(slot.user_id, {})[slot.work_date.weekday()] = slot
    return mapped


def _week_cabin_slot_map(week_start):
    week_end = week_start + timedelta(days=7)
    mapped = {}
    query = CabinAvailabilitySlot.query.filter(CabinAvailabilitySlot.work_date >= week_start, CabinAvailabilitySlot.work_date < week_end).order_by(CabinAvailabilitySlot.cabin_id, CabinAvailabilitySlot.work_date, CabinAvailabilitySlot.start_time)
    scope_id = _scope_institute_id()
    if scope_id is not None:
        query = query.join(Cabin, CabinAvailabilitySlot.cabin_id == Cabin.id).filter(Cabin.institute_id == scope_id)
    for slot in query.all():
        mapped.setdefault(slot.cabin_id, {})[slot.work_date.weekday()] = slot
    return mapped


def _week_days(week_start):
    return [{'date': week_start + timedelta(days=i), 'label': WEEKDAYS[i]} for i in range(7)]


def _active_appointments_exist(period_start, period_end, user_ids=None, cabin_ids=None):
    start_at = datetime.combine(period_start, datetime.min.time())
    end_at = datetime.combine(period_end, datetime.min.time())
    query = Appointment.query.filter(Appointment.status != 'cancelled', Appointment.start_at < end_at, Appointment.end_at > start_at)
    filters = []
    if user_ids:
        filters.append(Appointment.user_id.in_(user_ids))
    if cabin_ids:
        filters.append(Appointment.cabin_id.in_(cabin_ids))
    if filters:
        query = query.filter(or_(*filters))
    return query.first() is not None


def _workslot_conflict(user_id, start_at, end_at, exclude_id=None):
    query = WorkSlot.query.filter_by(user_id=user_id, work_date=start_at.date()).filter(WorkSlot.start_time < end_at.time(), WorkSlot.end_time > start_at.time())
    if exclude_id:
        query = query.filter(WorkSlot.id != exclude_id)
    return query.first() is not None


def _slot_contains_active_appointments(slot):
    start_at, end_at = _slot_bounds(slot)
    return Appointment.query.filter(
        Appointment.status != 'cancelled',
        Appointment.user_id == slot.user_id,
        Appointment.start_at >= start_at,
        Appointment.end_at <= end_at,
    ).first() is not None


def _ilu_error(user, treatment):
    skill = SkillILU.query.filter_by(user_id=user.id, treatment_id=treatment.id).first()
    if not skill or skill.level not in ('L', 'U'):
        return 'Cette praticienne n’est pas habilitée ILU L/U pour cette prestation.'
    return None


def _cabin_compatibility_error(treatment, cabin):
    rules = TreatmentCabinCompatibility.query.filter_by(treatment_id=treatment.id).all()
    if not rules:
        return None
    matching_rule = next((rule for rule in rules if rule.cabin_id == cabin.id), None)
    if not matching_rule or not matching_rule.is_allowed:
        return 'Cette cabine n’est pas compatible avec la prestation sélectionnée.'
    return None


def _appointment_validation_error(treatment, user, cabin, start_at, end_at, exclude_id=None):
    if not treatment.is_active:
        return 'Cette prestation est inactive.'
    if not user.is_active:
        return 'Cette praticienne est inactive.'
    if not cabin.is_active:
        return 'Cette cabine est inactive.'
    if not _entity_in_scope(user) or not _entity_in_scope(cabin) or not _entity_in_scope(treatment):
        return 'Cette ressource ne fait pas partie de votre établissement.'
    if user.institute_id and cabin.institute_id and user.institute_id != cabin.institute_id:
        return 'La cabine sélectionnée ne correspond pas à l’établissement de la praticienne.'
    if treatment.institute_id and user.institute_id and treatment.institute_id != user.institute_id:
        return 'La prestation ne correspond pas à l’établissement de la praticienne.'
    if treatment.institute_id and cabin.institute_id and treatment.institute_id != cabin.institute_id:
        return 'La prestation ne correspond pas à l’établissement de la cabine.'
    cabin_compatibility_message = _cabin_compatibility_error(treatment, cabin)
    if cabin_compatibility_message:
        return cabin_compatibility_message
    ilu_message = _ilu_error(user, treatment)
    if ilu_message:
        return ilu_message
    available, message = _user_is_available(user.id, start_at, end_at)
    if not available:
        return message
    cabin_available, cabin_message = _cabin_is_available(cabin.id, start_at, end_at)
    if not cabin_available:
        return cabin_message
    if _busy_appointment(Appointment.query.filter_by(user_id=user.id), start_at, end_at, exclude_id):
        return 'Conflit : cette praticienne a déjà un rendez-vous sur ce créneau.'
    if _busy_appointment(Appointment.query.filter_by(cabin_id=cabin.id), start_at, end_at, exclude_id):
        return 'Conflit : cette cabine est déjà occupée sur ce créneau.'
    return None


@planning_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        work_date = datetime.strptime(request.form['work_date'], '%Y-%m-%d').date()
        view = request.args.get('view', 'user')
        guard = _require_planning_manager_form(work_date, view) or _csrf_form_guard(work_date, view)
        if guard:
            return guard
        user = User.query.get_or_404(int(request.form['user_id']))
        if not _entity_in_scope(user):
            abort(403)
        start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
        if end_time <= start_time:
            flash('Horaire invalide.', 'error')
            return redirect(url_for('planning.index', date=work_date.isoformat(), view=view))
        ws = WorkSlot(user_id=user.id, work_date=work_date, start_time=start_time, end_time=end_time, status=request.form.get('status', 'present'), note=request.form.get('note', ''))
        db.session.add(ws)
        db.session.commit()
        return redirect(url_for('planning.index', date=work_date.isoformat(), view=view))

    selected_date = _parse_selected_date()
    selected_view = request.args.get('view', 'user')
    if selected_view not in ('user', 'cabin'):
        selected_view = 'user'
    selected_week_start = _week_start(selected_date)
    week_days = _week_days(selected_week_start)

    start_day, end_day = _day_bounds(selected_date)
    scope_id = _scope_institute_id()
    users_query = User.query.filter_by(is_active=True)
    cabins_query = Cabin.query.filter_by(is_active=True)
    treatments_query = Treatment.query.filter_by(is_active=True)
    if scope_id is not None:
        users_query = users_query.filter_by(institute_id=scope_id)
        cabins_query = cabins_query.filter_by(institute_id=scope_id)
        treatments_query = treatments_query.filter(or_(Treatment.institute_id == scope_id, Treatment.institute_id.is_(None)))
    users = users_query.order_by(User.first_name, User.last_name).all()
    cabins = cabins_query.order_by(Cabin.name).all()
    treatments = treatments_query.order_by(Treatment.category, Treatment.name).all()
    user_ids = [user.id for user in users]
    cabin_ids = [cabin.id for cabin in cabins]
    slots = WorkSlot.query.filter(WorkSlot.work_date == selected_date, WorkSlot.user_id.in_(user_ids or [-1])).all()
    cabin_slots = CabinAvailabilitySlot.query.filter(CabinAvailabilitySlot.work_date == selected_date, CabinAvailabilitySlot.cabin_id.in_(cabin_ids or [-1])).all()
    appointments = Appointment.query.filter(
        Appointment.start_at >= start_day,
        Appointment.start_at < end_day,
        or_(Appointment.user_id.in_(user_ids or [-1]), Appointment.cabin_id.in_(cabin_ids or [-1])),
    ).order_by(Appointment.start_at).all()

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

    return render_template(
        'planning/pro.html',
        users=users,
        cabins=cabins,
        treatments=treatments,
        slots=slots,
        appointments=appointments,
        selected_date=selected_date,
        selected_date_label=_date_label_fr(selected_date),
        selected_month_label=_month_label_fr(selected_date),
        prev_day=selected_date - timedelta(days=1),
        next_day=selected_date + timedelta(days=1),
        week_start=selected_week_start,
        prev_week=selected_week_start - timedelta(days=7),
        next_week=selected_week_start + timedelta(days=7),
        week_days=week_days,
        weekdays=WEEKDAYS,
        months=MONTHS,
        month_weeks=_month_matrix(selected_date),
        selected_view=selected_view,
        board_resources=board_resources,
        time_slots=_time_slots(),
        time_markers=_time_markers(),
        scheduler_start_hour=SCHEDULER_START_HOUR,
        scheduler_end_hour=SCHEDULER_END_HOUR,
        planning_csrf_token=_planning_csrf_token(),
        user_base_schedules=WeeklyUserSchedule.query.order_by(WeeklyUserSchedule.user_id, WeeklyUserSchedule.weekday, WeeklyUserSchedule.start_time).all(),
        cabin_base_schedules=WeeklyCabinSchedule.query.order_by(WeeklyCabinSchedule.cabin_id, WeeklyCabinSchedule.weekday, WeeklyCabinSchedule.start_time).all(),
        staff_base_slots=_base_user_schedule_map(),
        cabin_base_slots=_base_cabin_schedule_map(),
        staff_week_slots=_week_work_slot_map(selected_week_start),
        cabin_week_slots=_week_cabin_slot_map(selected_week_start),
    )


@planning_bp.route('/weekly-plan', methods=['POST'])
@login_required
def weekly_plan():
    week_start = _parse_week_start(request.form.get('week_start'))
    action = request.form.get('action', 'save_week_table')
    week_count = _parse_week_count()
    period_end = week_start + timedelta(days=7 * week_count)
    view = request.form.get('view', 'user')
    guard = _require_planning_manager_form(week_start, view) or _csrf_form_guard(week_start, view)
    if guard:
        return guard

    if action == 'save_week_table':
        try:
            user_ids = [int(value) for value in request.form.getlist('staff_user_id')]
            cabin_ids = [int(value) for value in request.form.getlist('cabin_id')]
        except ValueError:
            flash('Ressource invalide dans la planification.', 'error')
            return redirect(url_for('planning.index', date=week_start.isoformat(), view=view))
        if _active_appointments_exist(week_start, period_end, user_ids, cabin_ids):
            flash('Planification non enregistrée : des rendez-vous existent déjà sur la période ciblée. Modifiez les exceptions journée par journée.', 'error')
            return redirect(url_for('planning.index', date=week_start.isoformat(), view=view))
        if user_ids:
            WorkSlot.query.filter(WorkSlot.user_id.in_(user_ids), WorkSlot.work_date >= week_start, WorkSlot.work_date < period_end).delete(synchronize_session=False)
        if cabin_ids:
            CabinAvailabilitySlot.query.filter(CabinAvailabilitySlot.cabin_id.in_(cabin_ids), CabinAvailabilitySlot.work_date >= week_start, CabinAvailabilitySlot.work_date < period_end).delete(synchronize_session=False)
        try:
            for week_offset in range(week_count):
                target_week = week_start + timedelta(days=7 * week_offset)
                for user_id in user_ids:
                    user = User.query.get(user_id)
                    if not user or not _entity_in_scope(user):
                        raise ValueError('Praticienne hors périmètre')
                    for weekday in range(7):
                        if not request.form.get(f'staff_active_{user_id}_{weekday}'):
                            continue
                        start_time = datetime.strptime(request.form[f'staff_start_{user_id}_{weekday}'], '%H:%M').time()
                        end_time = datetime.strptime(request.form[f'staff_end_{user_id}_{weekday}'], '%H:%M').time()
                        if end_time <= start_time:
                            raise ValueError('Horaire praticienne invalide')
                        db.session.add(WorkSlot(user_id=user_id, work_date=target_week + timedelta(days=weekday), start_time=start_time, end_time=end_time, status=request.form.get(f'staff_status_{user_id}_{weekday}', AVAILABLE_STATUS), note=request.form.get(f'staff_note_{user_id}_{weekday}', '')))
                for cabin_id in cabin_ids:
                    cabin = Cabin.query.get(cabin_id)
                    if not cabin or not _entity_in_scope(cabin):
                        raise ValueError('Cabine hors périmètre')
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
            return redirect(url_for('planning.index', date=week_start.isoformat(), view=view))
        db.session.commit()
        flash(f'Planification enregistrée sur {week_count} semaine(s).', 'success')
        return redirect(url_for('planning.index', date=week_start.isoformat(), view=view))

    if action == 'generate_base':
        if _active_appointments_exist(week_start, period_end):
            flash('Génération bloquée : des rendez-vous existent déjà sur la période ciblée.', 'error')
            return redirect(url_for('planning.index', date=week_start.isoformat(), view=view))
        WorkSlot.query.filter(WorkSlot.work_date >= week_start, WorkSlot.work_date < period_end).delete(synchronize_session=False)
        CabinAvailabilitySlot.query.filter(CabinAvailabilitySlot.work_date >= week_start, CabinAvailabilitySlot.work_date < period_end).delete(synchronize_session=False)
        for week_offset in range(week_count):
            target_week = week_start + timedelta(days=7 * week_offset)
            for base in WeeklyUserSchedule.query.all():
                if _entity_in_scope(base.user):
                    db.session.add(_create_work_slot_from_base(base, target_week + timedelta(days=base.weekday)))
            for base in WeeklyCabinSchedule.query.all():
                if _entity_in_scope(base.cabin):
                    db.session.add(_create_cabin_slot_from_base(base, target_week + timedelta(days=base.weekday)))
        db.session.commit()
        flash(f'Semaine générée depuis les horaires de base sur {week_count} semaine(s).', 'success')
        return redirect(url_for('planning.index', date=week_start.isoformat(), view=view))

    work_date = datetime.strptime(request.form['work_date'], '%Y-%m-%d').date()
    start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
    end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
    if end_time <= start_time:
        flash('Horaire invalide.', 'error')
        return redirect(url_for('planning.index', date=work_date.isoformat(), view=view))
    if request.form.get('resource_type') == 'cabin':
        cabin = Cabin.query.get_or_404(int(request.form['cabin_id']))
        if not _entity_in_scope(cabin):
            abort(403)
        db.session.add(CabinAvailabilitySlot(cabin_id=cabin.id, work_date=work_date, start_time=start_time, end_time=end_time, status=request.form.get('cabin_status', CABIN_AVAILABLE_STATUS), note=request.form.get('note', '')))
    else:
        user = User.query.get_or_404(int(request.form['user_id']))
        if not _entity_in_scope(user):
            abort(403)
        db.session.add(WorkSlot(user_id=user.id, work_date=work_date, start_time=start_time, end_time=end_time, status=request.form.get('user_status', AVAILABLE_STATUS), note=request.form.get('note', '')))
    db.session.commit()
    flash('Créneau ajouté à la semaine.', 'success')
    return redirect(url_for('planning.index', date=work_date.isoformat(), view=view))


@planning_bp.route('/week-print')
@login_required
def week_print():
    week_start = _parse_week_start(request.args.get('date'))
    week_end = week_start + timedelta(days=7)
    scope_id = _scope_institute_id()
    users_query = User.query.filter_by(is_active=True)
    cabins_query = Cabin.query.filter_by(is_active=True)
    if scope_id is not None:
        users_query = users_query.filter_by(institute_id=scope_id)
        cabins_query = cabins_query.filter_by(institute_id=scope_id)
    users = users_query.order_by(User.first_name, User.last_name).all()
    cabins = cabins_query.order_by(Cabin.name).all()
    user_ids = [user.id for user in users]
    cabin_ids = [cabin.id for cabin in cabins]
    appointments = Appointment.query.filter(
        Appointment.start_at >= week_start,
        Appointment.start_at < week_end,
        or_(Appointment.user_id.in_(user_ids or [-1]), Appointment.cabin_id.in_(cabin_ids or [-1])),
    ).order_by(Appointment.start_at).all()
    appointments_by_day = {i: [] for i in range(7)}
    for appointment in appointments:
        appointments_by_day[appointment.start_at.date().weekday()].append(appointment)
    return render_template('planning/week_print.html', week_start=week_start, week_days=_week_days(week_start), week_label=f"{_date_label_fr(week_start)} - {_date_label_fr(week_end - timedelta(days=1))}", users=users, cabins=cabins, staff_week_slots=_week_work_slot_map(week_start), cabin_week_slots=_week_cabin_slot_map(week_start), appointments_by_day=appointments_by_day, weekdays=WEEKDAYS)


@planning_bp.route('/appointment/create', methods=['POST'])
@login_required
def create_appointment():
    selected_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
    view = request.form.get('view', 'user')
    guard = _require_planning_manager_form(selected_date, view) or _csrf_form_guard(selected_date, view)
    if guard:
        return guard
    treatment = Treatment.query.get_or_404(int(request.form['treatment_id']))
    user = User.query.get_or_404(int(request.form['user_id']))
    cabin = Cabin.query.get_or_404(int(request.form['cabin_id']))
    start_time = datetime.strptime(request.form['time'], '%H:%M').time()
    start_at = datetime.combine(selected_date, start_time)
    end_at = start_at + timedelta(minutes=treatment.duration_minutes or 60)

    message = _appointment_validation_error(treatment, user, cabin, start_at, end_at)
    if message:
        flash(message, 'error')
        return redirect(url_for('planning.index', date=selected_date.isoformat(), view=view))

    appointment = Appointment(
        customer_name=request.form['customer_name'],
        customer_email=request.form.get('customer_email', ''),
        treatment_id=treatment.id,
        user_id=user.id,
        cabin_id=cabin.id,
        start_at=start_at,
        end_at=end_at,
        status='confirmed',
        note=request.form.get('note', '').strip(),
    )
    db.session.add(appointment)
    db.session.commit()
    flash('Rendez-vous créé depuis le planning.', 'success')
    return redirect(url_for('planning.index', date=selected_date.isoformat(), view=view))


@planning_bp.route('/api/move', methods=['POST'])
@login_required
def move_event():
    guard = _require_planning_manager_json() or _csrf_json_guard()
    if guard:
        return guard
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
        treatment = appointment.treatment
        if resource_type == 'user':
            user = User.query.get_or_404(resource_id)
            cabin = appointment.cabin
            message = _appointment_validation_error(treatment, user, cabin, target_start, target_end, appointment.id)
            if message:
                cabin = _free_cabin(user.institute_id, target_start, target_end, appointment.id, treatment)
                if not cabin:
                    return jsonify({'ok': False, 'message': message or 'Aucune cabine libre'}), 409
                message = _appointment_validation_error(treatment, user, cabin, target_start, target_end, appointment.id)
            if message:
                return jsonify({'ok': False, 'message': message}), 409
            appointment.user_id = user.id
            appointment.cabin_id = cabin.id
        elif resource_type == 'cabin':
            cabin = Cabin.query.get_or_404(resource_id)
            user = appointment.user
            message = _appointment_validation_error(treatment, user, cabin, target_start, target_end, appointment.id)
            if message:
                return jsonify({'ok': False, 'message': message}), 409
            appointment.cabin_id = cabin.id
        else:
            return jsonify({'ok': False, 'message': 'Ressource invalide'}), 400
        appointment.start_at = target_start
        appointment.end_at = target_end
        db.session.commit()
        return jsonify({'ok': True})

    if event_type == 'slot' and resource_type == 'user':
        slot = WorkSlot.query.get_or_404(event_id)
        target_user = User.query.get_or_404(resource_id)
        if not _entity_in_scope(slot.user) or not _entity_in_scope(target_user):
            return jsonify({'ok': False, 'message': 'Ressource hors périmètre'}), 403
        if _slot_contains_active_appointments(slot):
            return jsonify({'ok': False, 'message': 'Impossible de déplacer ce créneau : il contient déjà un rendez-vous actif.'}), 409
        duration = datetime.combine(slot.work_date, slot.end_time) - datetime.combine(slot.work_date, slot.start_time)
        new_end = target_start + duration
        if new_end.date() != target_date:
            return jsonify({'ok': False, 'message': 'Le créneau doit rester sur la même journée'}), 409
        if _workslot_conflict(target_user.id, target_start, new_end, slot.id):
            return jsonify({'ok': False, 'message': 'Conflit : cette praticienne a déjà un créneau sur cette période.'}), 409
        slot.user_id = target_user.id
        slot.work_date = target_date
        slot.start_time = target_start.time()
        slot.end_time = new_end.time()
        db.session.commit()
        return jsonify({'ok': True})

    return jsonify({'ok': False, 'message': 'Mouvement impossible'}), 400
