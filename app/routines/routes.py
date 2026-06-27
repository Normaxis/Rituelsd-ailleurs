import base64
import io
from datetime import date, datetime, timedelta

import qrcode
from flask import Blueprint, render_template, request, redirect, url_for
from sqlalchemy import or_

from app.extensions import db
from app.models import Routine, Cabin, User, RoutineCompletion
from app.utils.auth import login_required

routines_bp = Blueprint('routines', __name__)
WEEK_LABELS = ['L', 'M', 'M', 'J', 'V', 'S', 'D']
MONTHS = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']


def _user_from_code(code):
    value = ''.join(char for char in (code or '') if char.isdigit())
    if len(value) != 6:
        return None
    return User.query.filter_by(is_active=True, routine_code=value).first()


def _qr_data_uri(url):
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    payload = base64.b64encode(buffer.getvalue()).decode('ascii')
    return 'data:image/png;base64,' + payload


def _qr_items(cabins):
    items = []
    for cabin in cabins:
        scan_url = url_for('routines.cabin_scan', cabin_id=cabin.id, _external=True)
        items.append({'cabin': cabin, 'url': scan_url, 'qr': _qr_data_uri(scan_url)})
    return items


def _week_start(day):
    return day - timedelta(days=day.weekday())


def _week_days(day):
    start = _week_start(day)
    return [{'date': start + timedelta(days=index), 'label': WEEK_LABELS[index], 'number': (start + timedelta(days=index)).day, 'is_today': start + timedelta(days=index) == day} for index in range(7)]


def _routine_scope_key(routine):
    return routine.cabin_id or 0


def _completion_map(start_day, end_day):
    completions = RoutineCompletion.query.filter(RoutineCompletion.completed_on >= start_day, RoutineCompletion.completed_on <= end_day).all()
    mapped = {}
    for item in completions:
        key = (item.routine_id, item.cabin_id or 0, item.completed_on)
        mapped.setdefault(key, []).append(item)
    return mapped, completions


def _routine_cards(routines, start_day, days):
    mapped, completions = _completion_map(start_day, start_day + timedelta(days=len(days) - 1))
    cards = []
    total_expected = 0
    total_done = 0
    total_late = 0
    for routine in routines:
        scope_key = _routine_scope_key(routine)
        day_stats = []
        for day in days:
            is_weekend = day['date'].weekday() >= 5
            key = (routine.id, scope_key, day['date'])
            done_items = mapped.get(key, [])
            if done_items:
                color = 'green'
                label = '1/1'
                total_done += 1
            elif is_weekend:
                color = 'gray'
                label = '-'
            elif day['date'] < date.today():
                color = 'red'
                label = '0/1'
                total_late += 1
            else:
                color = 'orange'
                label = '0/1'
            if not is_weekend:
                total_expected += 1
            day_stats.append({'date': day['date'], 'label': label, 'color': color, 'done': bool(done_items), 'items': done_items})
        done_weekdays = sum(1 for item in day_stats[:5] if item['done'])
        rate = round((done_weekdays / 5) * 100) if day_stats else 0
        cards.append({'routine': routine, 'day_stats': day_stats, 'rate': rate})
    pending = max(total_expected - total_done - total_late, 0)
    summary = {'total': total_expected, 'done': total_done, 'pending': pending, 'late': total_late, 'completion_rate': round((total_done / total_expected) * 100) if total_expected else 0}
    return cards, summary, completions


def _parse_report_date(value, fallback):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date() if value else fallback
    except ValueError:
        return fallback


@routines_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        cabin_value = request.form.get('cabin_id') or ''
        cabin_id = int(cabin_value) if cabin_value else None
        r = Routine(name=request.form['name'], cabin_id=cabin_id, instructions=request.form.get('instructions',''))
        db.session.add(r)
        db.session.commit()
        return redirect(url_for('routines.index'))

    today = date.today()
    days = _week_days(today)
    routines = Routine.query.order_by(Routine.name).all()
    cards, summary, completions = _routine_cards(routines, _week_start(today), days)
    cabins = Cabin.query.order_by(Cabin.name).all()
    return render_template('routines/index.html', routines=routines, routine_cards=cards, cabins=cabins, qr_items=_qr_items(cabins), week_days=days, summary=summary, completions=completions, calendar_label=MONTHS[today.month - 1] + ' ' + str(today.year), week_number=today.isocalendar().week)


@routines_bp.route('/rapport')
@login_required
def report():
    today = date.today()
    start_day = _parse_report_date(request.args.get('start'), _week_start(today))
    end_day = _parse_report_date(request.args.get('end'), start_day + timedelta(days=6))
    if end_day < start_day:
        end_day = start_day
    days = [{'date': start_day + timedelta(days=index), 'label': WEEK_LABELS[(start_day + timedelta(days=index)).weekday()], 'number': (start_day + timedelta(days=index)).day, 'is_today': start_day + timedelta(days=index) == today} for index in range((end_day - start_day).days + 1)]
    routines = Routine.query.order_by(Routine.name).all()
    cards, summary, completions = _routine_cards(routines, start_day, days)
    return render_template('routines/report.html', start_day=start_day, end_day=end_day, routine_cards=cards, summary=summary, completions=completions, days=days, generated_at=datetime.now())


@routines_bp.route('/cabine/<int:cabin_id>/scan', methods=['GET','POST'])
def cabin_scan(cabin_id):
    cabin = Cabin.query.get_or_404(cabin_id)
    routines = Routine.query.filter(or_(Routine.cabin_id == cabin.id, Routine.cabin_id.is_(None))).order_by(Routine.cabin_id.desc(), Routine.name).all()
    today = date.today()
    completions = RoutineCompletion.query.filter_by(cabin_id=cabin.id, completed_on=today).all()
    completed_ids = {item.routine_id for item in completions}
    message = None
    error = None

    if request.method == 'POST':
        reference = request.form.get('staff_code') or request.form.get('agent_ref')
        user = _user_from_code(reference)
        selected_ids = [int(value) for value in request.form.getlist('routine_ids')]
        if not user:
            error = 'Code routine invalide.'
        elif not selected_ids:
            error = 'Selectionne au moins une routine a valider.'
        else:
            for routine_id in selected_ids:
                existing = RoutineCompletion.query.filter_by(routine_id=routine_id, cabin_id=cabin.id, user_id=user.id, completed_on=today).first()
                if not existing:
                    completion = RoutineCompletion(routine_id=routine_id, cabin_id=cabin.id, user_id=user.id, completed_on=today, status='done', note=request.form.get('note',''))
                    db.session.add(completion)
            db.session.commit()
            message = 'Routines validees. Bonne prise de poste.'
            completions = RoutineCompletion.query.filter_by(cabin_id=cabin.id, completed_on=today).all()
            completed_ids = {item.routine_id for item in completions}

    return render_template('routines/scan.html', cabin=cabin, routines=routines, completed_ids=completed_ids, completions=completions, message=message, error=error, today=today)
