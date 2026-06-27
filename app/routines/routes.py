import base64
import io
from datetime import date, datetime, timedelta

import qrcode
from flask import Blueprint, Response, abort, flash, render_template, request, redirect, url_for
from sqlalchemy import or_

from app.extensions import db
from app.models import Cabin, QSEAction, Routine, RoutineCompletion, RoutineIssue, RoutineProofPhoto, RoutineReferencePhoto, RoutineStep, RoutineStepCheck, User
from app.utils.auth import login_required

routines_bp = Blueprint('routines', __name__)
WEEK_LABELS = ['L', 'M', 'M', 'J', 'V', 'S', 'D']
MONTHS = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']
ALLOWED_PHOTO_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_PHOTO_BYTES = 3 * 1024 * 1024


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
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def _qr_items(cabins):
    return [{'cabin': cabin, 'url': url_for('routines.cabin_scan', cabin_id=cabin.id, _external=True), 'qr': _qr_data_uri(url_for('routines.cabin_scan', cabin_id=cabin.id, _external=True))} for cabin in cabins]


def _week_start(day):
    return day - timedelta(days=day.weekday())


def _week_days(day):
    start = _week_start(day)
    return [{'date': start + timedelta(days=index), 'label': WEEK_LABELS[index], 'number': (start + timedelta(days=index)).day, 'is_today': start + timedelta(days=index) == day} for index in range(7)]


def _completion_map(start_day, end_day):
    items = RoutineCompletion.query.filter(RoutineCompletion.completed_on >= start_day, RoutineCompletion.completed_on <= end_day).all()
    mapped = {}
    for item in items:
        key = (item.routine_id, item.cabin_id or 0, item.completed_on)
        mapped.setdefault(key, []).append(item)
    return mapped, items


def _routine_cards(routines, start_day, days):
    mapped, validations = _completion_map(start_day, start_day + timedelta(days=len(days) - 1))
    cards = []
    total_expected = 0
    total_done = 0
    total_late = 0
    for routine in routines:
        scope_key = routine.cabin_id or 0
        day_stats = []
        for day in days:
            is_weekend = day['date'].weekday() >= 5
            done_items = mapped.get((routine.id, scope_key, day['date']), [])
            if done_items:
                color, label = 'green', '1/1'
                total_done += 1
            elif is_weekend:
                color, label = 'gray', '-'
            elif day['date'] < date.today():
                color, label = 'red', '0/1'
                total_late += 1
            else:
                color, label = 'orange', '0/1'
            if not is_weekend:
                total_expected += 1
            day_stats.append({'date': day['date'], 'label': label, 'color': color, 'done': bool(done_items), 'items': done_items})
        done_weekdays = sum(1 for item in day_stats[:5] if item['done'])
        cards.append({'routine': routine, 'day_stats': day_stats, 'rate': round((done_weekdays / 5) * 100) if day_stats else 0})
    pending = max(total_expected - total_done - total_late, 0)
    summary = {'total': total_expected, 'done': total_done, 'pending': pending, 'late': total_late, 'completion_rate': round((total_done / total_expected) * 100) if total_expected else 0}
    return cards, summary, validations


def _steps_for_routine(routine):
    steps = sorted(list(getattr(routine, 'steps', []) or []), key=lambda item: item.position or 0)
    if steps:
        return steps
    lines = [line.strip() for line in (routine.instructions or '').splitlines() if line.strip()]
    return [RoutineStep(routine_id=routine.id, position=index + 1, title=line) for index, line in enumerate(lines)]


def _store_photo(uploaded, target, kind='proof'):
    if not uploaded or not uploaded.filename or uploaded.mimetype not in ALLOWED_PHOTO_TYPES:
        return None
    data = uploaded.read()
    if not data or len(data) > MAX_PHOTO_BYTES:
        return None
    if isinstance(target, Routine):
        return RoutineReferencePhoto(routine_id=target.id, title='Reference', filename=uploaded.filename, mime_type=uploaded.mimetype, image_data=data)
    return RoutineProofPhoto(completion_id=target.id, kind=kind, filename=uploaded.filename, mime_type=uploaded.mimetype, image_data=data)


@routines_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        cabin_value = request.form.get('cabin_id') or ''
        cabin_id = int(cabin_value) if cabin_value else None
        steps_text = request.form.get('steps') or request.form.get('instructions') or ''
        routine = Routine(name=request.form['name'], cabin_id=cabin_id, instructions=steps_text)
        db.session.add(routine)
        db.session.flush()
        for index, line in enumerate([line.strip() for line in steps_text.splitlines() if line.strip()]):
            db.session.add(RoutineStep(routine_id=routine.id, position=index + 1, title=line, is_required=True))
        for uploaded in request.files.getlist('reference_photos'):
            photo = _store_photo(uploaded, routine, 'reference')
            if photo:
                db.session.add(photo)
        db.session.commit()
        flash('Routine creee avec etapes et references.', 'success')
        return redirect(url_for('routines.index'))

    today = date.today()
    days = _week_days(today)
    routines = Routine.query.order_by(Routine.name).all()
    cards, summary, validations = _routine_cards(routines, _week_start(today), days)
    cabins = Cabin.query.order_by(Cabin.name).all()
    return render_template('routines/index.html', routines=routines, routine_cards=cards, cabins=cabins, qr_items=_qr_items(cabins), week_days=days, summary=summary, completions=validations, calendar_label=MONTHS[today.month - 1] + ' ' + str(today.year), week_number=today.isocalendar().week)


@routines_bp.route('/rapport/<int:validation_id>')
@login_required
def report(validation_id):
    validation = RoutineCompletion.query.get_or_404(validation_id)
    steps = _steps_for_routine(validation.routine)
    return render_template('routines/report.html', validation=validation, steps=steps, generated_at=datetime.now())


@routines_bp.route('/photo-reference/<int:photo_id>')
@login_required
def reference_photo(photo_id):
    photo = RoutineReferencePhoto.query.get_or_404(photo_id)
    return Response(photo.image_data, mimetype=photo.mime_type)


@routines_bp.route('/photo-preuve/<int:photo_id>')
@login_required
def proof_photo(photo_id):
    photo = RoutineProofPhoto.query.get_or_404(photo_id)
    return Response(photo.image_data, mimetype=photo.mime_type)


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
        user = _user_from_code(request.form.get('agent_ref'))
        routine = Routine.query.get_or_404(int(request.form.get('routine_id')))
        step_ids = [int(value) for value in request.form.getlist('step_ids')]
        steps = _steps_for_routine(routine)
        required_ids = {step.id for step in steps if getattr(step, 'id', None) and step.is_required}
        if not user:
            error = 'Code routine invalide.'
        elif required_ids and not required_ids.issubset(set(step_ids)):
            error = 'Toutes les actions obligatoires doivent etre cochees.'
        else:
            completion = RoutineCompletion.query.filter_by(routine_id=routine.id, cabin_id=cabin.id, user_id=user.id, completed_on=today).first()
            if not completion:
                completion = RoutineCompletion(routine_id=routine.id, cabin_id=cabin.id, user_id=user.id, completed_on=today, status='done', note=request.form.get('note',''))
                db.session.add(completion)
                db.session.flush()
            completion.note = request.form.get('note','')
            for step_id in step_ids:
                if not RoutineStepCheck.query.filter_by(completion_id=completion.id, step_id=step_id).first():
                    db.session.add(RoutineStepCheck(completion_id=completion.id, step_id=step_id, checked=True))
            for uploaded in request.files.getlist('proof_photos'):
                photo = _store_photo(uploaded, completion, 'proof')
                if photo:
                    db.session.add(photo)
            issue_title = request.form.get('issue_title','').strip()
            if issue_title:
                issue = RoutineIssue(completion_id=completion.id, title=issue_title, description=request.form.get('issue_description',''), severity=request.form.get('issue_severity','medium'))
                db.session.add(issue)
                db.session.add(QSEAction(source='Routine', theme='Exploitation', title=issue_title, description='Probleme detecte pendant la routine : ' + (request.form.get('issue_description','') or routine.name), responsible=user.full_name, status='open'))
            db.session.commit()
            message = 'Routine validee. Les preuves et problemes eventuels sont enregistres.'
            completions = RoutineCompletion.query.filter_by(cabin_id=cabin.id, completed_on=today).all()
            completed_ids = {item.routine_id for item in completions}

    routine_steps = {routine.id: _steps_for_routine(routine) for routine in routines}
    return render_template('routines/scan.html', cabin=cabin, routines=routines, routine_steps=routine_steps, completed_ids=completed_ids, completions=completions, message=message, error=error, today=today)
