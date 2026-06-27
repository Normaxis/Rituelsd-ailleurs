import base64
import io
from datetime import date

import qrcode
from flask import Blueprint, render_template, request, redirect, url_for
from sqlalchemy import or_

from app.extensions import db
from app.models import Routine, Cabin, User, RoutineCompletion
from app.utils.auth import login_required

routines_bp = Blueprint('routines', __name__)


def _staff_code(user):
    return str(100000 + (user.id or 0))[-6:]


def _user_from_code(code):
    cleaned = ''.join(char for char in (code or '') if char.isdigit())
    if len(cleaned) != 6:
        return None
    for user in User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all():
        if _staff_code(user) == cleaned:
            return user
    return None


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


def _staff_codes():
    return [{'user': user, 'code': _staff_code(user)} for user in User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all()]


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

    cabins = Cabin.query.order_by(Cabin.name).all()
    return render_template('routines/index.html', routines=Routine.query.order_by(Routine.name).all(), cabins=cabins, qr_items=_qr_items(cabins), staff_codes=_staff_codes())


@routines_bp.route('/qr-cabines')
@login_required
def qr_cabins():
    cabins = Cabin.query.order_by(Cabin.name).all()
    completions = RoutineCompletion.query.filter_by(completed_on=date.today()).order_by(RoutineCompletion.created_at.desc()).all()
    return render_template('routines/qr_cabins.html', qr_items=_qr_items(cabins), staff_codes=_staff_codes(), completions=completions)


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
            error = 'Reference equipe invalide.'
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
