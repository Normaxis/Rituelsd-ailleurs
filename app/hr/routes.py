from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import HabilitationRecord, Institute, Role, TrainingRecord, User, WorkSlot
from app.utils.auth import login_required

hr_bp = Blueprint('hr', __name__)

def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None

def parse_time(value):
    return datetime.strptime(value, '%H:%M').time() if value else None

@hr_bp.route('/')
@login_required
def dashboard():
    today = date.today()
    soon = today + timedelta(days=60)
    users = User.query.order_by(User.first_name, User.last_name).all()
    trainings_due = TrainingRecord.query.filter(TrainingRecord.expires_on != None, TrainingRecord.expires_on <= soon).order_by(TrainingRecord.expires_on).all()
    habilitations_due = HabilitationRecord.query.filter(HabilitationRecord.expires_on != None, HabilitationRecord.expires_on <= soon).order_by(HabilitationRecord.expires_on).all()
    week_slots = WorkSlot.query.filter(WorkSlot.work_date >= today, WorkSlot.work_date <= today + timedelta(days=7)).order_by(WorkSlot.work_date, WorkSlot.start_time).all()
    return render_template('hr/dashboard.html', users=users, trainings_due=trainings_due, habilitations_due=habilitations_due, week_slots=week_slots, today=today)

@hr_bp.route('/personnel', methods=['GET','POST'])
@login_required
def personnel():
    if request.method == 'POST':
        user = User(first_name=request.form['first_name'], last_name=request.form['last_name'], username=request.form['username'], role_id=int(request.form['role_id']), institute_id=int(request.form['institute_id']) if request.form.get('institute_id') else None, is_active=True)
        user.set_password(request.form.get('password') or 'rituels123')
        db.session.add(user)
        db.session.commit()
        flash('Salarie ajoute.', 'success')
        return redirect(url_for('hr.personnel'))
    return render_template('hr/personnel.html', users=User.query.order_by(User.first_name, User.last_name).all(), roles=Role.query.all(), institutes=Institute.query.all())

@hr_bp.route('/formations', methods=['GET','POST'])
@login_required
def trainings():
    if request.method == 'POST':
        item = TrainingRecord(user_id=int(request.form['user_id']), title=request.form['title'], category=request.form.get('category','Formation'), provider=request.form.get('provider',''), completed_on=parse_date(request.form.get('completed_on')), expires_on=parse_date(request.form.get('expires_on')), status=request.form.get('status','planned'), note=request.form.get('note',''))
        db.session.add(item)
        work_date = parse_date(request.form.get('work_date'))
        start_time = parse_time(request.form.get('start_time'))
        end_time = parse_time(request.form.get('end_time'))
        if work_date and start_time and end_time:
            db.session.add(WorkSlot(user_id=item.user_id, work_date=work_date, start_time=start_time, end_time=end_time, status='training', note=item.title))
        db.session.commit()
        return redirect(url_for('hr.trainings'))
    return render_template('hr/formations.html', records=TrainingRecord.query.order_by(TrainingRecord.expires_on).all(), users=User.query.order_by(User.first_name, User.last_name).all())

@hr_bp.route('/habilitations', methods=['GET','POST'])
@login_required
def habilitations():
    if request.method == 'POST':
        item = HabilitationRecord(user_id=int(request.form['user_id']), name=request.form['name'], level=request.form.get('level',''), issued_on=parse_date(request.form.get('issued_on')), expires_on=parse_date(request.form.get('expires_on')), status=request.form.get('status','valid'), note=request.form.get('note',''))
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('hr.habilitations'))
    return render_template('hr/habilitations.html', records=HabilitationRecord.query.order_by(HabilitationRecord.expires_on).all(), users=User.query.order_by(User.first_name, User.last_name).all())
