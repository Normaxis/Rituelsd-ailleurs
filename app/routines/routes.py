from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Routine, Cabin, User, WorkSlot, TrainingRecord, HabilitationRecord
from app.utils.auth import login_required

routines_bp = Blueprint('routines', __name__)

def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None

@routines_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        r = Routine(name=request.form['name'], cabin_id=int(request.form['cabin_id']), instructions=request.form['instructions'])
        db.session.add(r); db.session.commit()
        return redirect(url_for('routines.index'))
    return render_template('routines/index.html', routines=Routine.query.all(), cabins=Cabin.query.all())

@routines_bp.route('/rh')
@login_required
def hr_dashboard():
    today = date.today()
    soon = today + timedelta(days=60)
    users = User.query.order_by(User.first_name, User.last_name).all()
    trainings_due = TrainingRecord.query.filter(TrainingRecord.expires_on != None, TrainingRecord.expires_on <= soon).order_by(TrainingRecord.expires_on).all()
    habilitations_due = HabilitationRecord.query.filter(HabilitationRecord.expires_on != None, HabilitationRecord.expires_on <= soon).order_by(HabilitationRecord.expires_on).all()
    week_slots = WorkSlot.query.filter(WorkSlot.work_date >= today, WorkSlot.work_date <= today + timedelta(days=7)).all()
    return render_template('hr/dashboard.html', users=users, trainings_due=trainings_due, habilitations_due=habilitations_due, week_slots=week_slots, today=today)

@routines_bp.route('/rh/formations', methods=['GET','POST'])
@login_required
def trainings():
    if request.method == 'POST':
        item = TrainingRecord(user_id=int(request.form['user_id']), title=request.form['title'], category=request.form.get('category','Formation'), provider=request.form.get('provider',''), completed_on=parse_date(request.form.get('completed_on')), expires_on=parse_date(request.form.get('expires_on')), status=request.form.get('status','planned'), note=request.form.get('note',''))
        db.session.add(item); db.session.commit()
        return redirect(url_for('routines.trainings'))
    records = TrainingRecord.query.order_by(TrainingRecord.expires_on).all()
    users = User.query.order_by(User.first_name, User.last_name).all()
    return render_template('hr/formations.html', records=records, users=users)

@routines_bp.route('/rh/habilitations', methods=['GET','POST'])
@login_required
def habilitations():
    if request.method == 'POST':
        item = HabilitationRecord(user_id=int(request.form['user_id']), name=request.form['name'], level=request.form.get('level',''), issued_on=parse_date(request.form.get('issued_on')), expires_on=parse_date(request.form.get('expires_on')), status=request.form.get('status','valid'), note=request.form.get('note',''))
        db.session.add(item); db.session.commit()
        return redirect(url_for('routines.habilitations'))
    records = HabilitationRecord.query.order_by(HabilitationRecord.expires_on).all()
    users = User.query.order_by(User.first_name, User.last_name).all()
    return render_template('hr/habilitations.html', records=records, users=users)
