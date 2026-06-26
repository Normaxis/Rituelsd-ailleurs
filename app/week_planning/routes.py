from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, session
from sqlalchemy import or_

from app.models import Appointment, Cabin, CabinAvailabilitySlot, User, WorkSlot
from app.utils.auth import login_required

week_planning_bp = Blueprint('week_planning', __name__)

WEEKDAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
MONTHS = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']


def _week_start(value):
    return value - timedelta(days=value.weekday())


def _parse_selected_date():
    raw_value = request.args.get('date')
    try:
        return datetime.strptime(raw_value, '%Y-%m-%d').date() if raw_value else date.today()
    except ValueError:
        return date.today()


def _current_user():
    user_id = session.get('user_id')
    return User.query.get(user_id) if user_id else None


def _scope_institute_id():
    user = _current_user()
    if not user or session.get('role') == 'general_admin':
        return None
    return user.institute_id


def _date_label(value):
    return f"{WEEKDAYS[value.weekday()]} {value.day:02d} {MONTHS[value.month - 1]}"


@week_planning_bp.route('/')
@login_required
def index():
    selected_date = _parse_selected_date()
    week_start = _week_start(selected_date)
    week_end = week_start + timedelta(days=7)
    scope_id = _scope_institute_id()

    users_query = User.query.filter_by(is_active=True)
    cabins_query = Cabin.query.filter_by(is_active=True)
    if scope_id is not None:
        users_query = users_query.filter_by(institute_id=scope_id)
        cabins_query = cabins_query.filter_by(institute_id=scope_id)

    users = users_query.order_by(User.first_name, User.last_name).all()
    cabins = cabins_query.order_by(Cabin.name).all()
    user_ids = [item.id for item in users]
    cabin_ids = [item.id for item in cabins]

    appointments = Appointment.query.filter(
        Appointment.start_at >= datetime.combine(week_start, datetime.min.time()),
        Appointment.start_at < datetime.combine(week_end, datetime.min.time()),
        or_(Appointment.user_id.in_(user_ids or [-1]), Appointment.cabin_id.in_(cabin_ids or [-1])),
    ).order_by(Appointment.start_at).all()

    work_slots = WorkSlot.query.filter(
        WorkSlot.work_date >= week_start,
        WorkSlot.work_date < week_end,
        WorkSlot.user_id.in_(user_ids or [-1]),
    ).order_by(WorkSlot.work_date, WorkSlot.start_time).all()

    cabin_slots = CabinAvailabilitySlot.query.filter(
        CabinAvailabilitySlot.work_date >= week_start,
        CabinAvailabilitySlot.work_date < week_end,
        CabinAvailabilitySlot.cabin_id.in_(cabin_ids or [-1]),
    ).order_by(CabinAvailabilitySlot.work_date, CabinAvailabilitySlot.start_time).all()

    days = []
    for offset in range(7):
        current_day = week_start + timedelta(days=offset)
        day_appointments = [item for item in appointments if item.start_at.date() == current_day]
        day_work_slots = [item for item in work_slots if item.work_date == current_day]
        day_cabin_slots = [item for item in cabin_slots if item.work_date == current_day]
        available_staff_count = len({slot.user_id for slot in day_work_slots if slot.status == 'present'})
        available_cabin_count = len({slot.cabin_id for slot in day_cabin_slots if slot.status == 'available'})
        days.append({
            'date': current_day,
            'label': _date_label(current_day),
            'is_today': current_day == date.today(),
            'appointments': day_appointments,
            'work_slots': day_work_slots,
            'cabin_slots': day_cabin_slots,
            'available_staff_count': available_staff_count,
            'available_cabin_count': available_cabin_count,
        })

    return render_template(
        'planning/week_overview.html',
        selected_date=selected_date,
        week_start=week_start,
        week_end=week_end,
        prev_week=week_start - timedelta(days=7),
        next_week=week_start + timedelta(days=7),
        days=days,
        appointments=appointments,
        users=users,
        cabins=cabins,
        total_appointments=len(appointments),
        confirmed_count=len([item for item in appointments if item.status == 'confirmed']),
        completed_count=len([item for item in appointments if item.status == 'completed']),
        cancelled_count=len([item for item in appointments if item.status == 'cancelled']),
    )
