from datetime import date, datetime, timedelta
from flask import Blueprint, Response, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Cabin, HabilitationRecord, Institute, Role, TrainingRecord, User, UserPhoto, WorkSlot, WeeklyCabinSchedule, WeeklyUserSchedule
from app.utils.auth import login_required

hr_bp = Blueprint('hr', __name__)

WEEKDAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
ALLOWED_PHOTO_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None


def parse_time(value):
    return datetime.strptime(value, '%H:%M').time() if value else None


def user_week_schedule_map():
    schedules = WeeklyUserSchedule.query.order_by(WeeklyUserSchedule.user_id, WeeklyUserSchedule.weekday, WeeklyUserSchedule.start_time).all()
    mapped = {}
    for item in schedules:
        mapped.setdefault(item.user_id, {})[item.weekday] = item
    return mapped


def user_photo_ids():
    return {photo.user_id: photo.id for photo in UserPhoto.query.all()}


def clean_routine_code(value):
    return ''.join(char for char in (value or '') if char.isdigit())[:6]


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
        routine_code = clean_routine_code(request.form.get('routine_code'))
        user = User(first_name=request.form['first_name'], last_name=request.form['last_name'], username=request.form['username'], role_id=int(request.form['role_id']), institute_id=int(request.form['institute_id']) if request.form.get('institute_id') else None, is_active=True)
        user.set_password(request.form.get('password') or 'rituels123')
        user.routine_code = routine_code
        db.session.add(user)
        db.session.commit()
        if not user.routine_code:
            user.routine_code = str(100000 + user.id)[-6:]
            db.session.commit()
        flash('Salarie ajoute.', 'success')
        return redirect(url_for('hr.personnel'))
    users = User.query.filter_by(is_active=True).order_by(User.first_name, User.last_name).all()
    return render_template('hr/personnel.html', users=users, roles=Role.query.all(), institutes=Institute.query.all(), cabins=Cabin.query.order_by(Cabin.name).all(), user_base_schedules=WeeklyUserSchedule.query.order_by(WeeklyUserSchedule.user_id, WeeklyUserSchedule.weekday, WeeklyUserSchedule.start_time).all(), user_week_schedules=user_week_schedule_map(), user_photo_ids=user_photo_ids(), cabin_base_schedules=WeeklyCabinSchedule.query.order_by(WeeklyCabinSchedule.cabin_id, WeeklyCabinSchedule.weekday, WeeklyCabinSchedule.start_time).all(), weekdays=WEEKDAYS)


@hr_bp.route('/personnel/routine-code', methods=['POST'])
@login_required
def save_routine_code():
    user = User.query.get_or_404(int(request.form['user_id']))
    routine_code = clean_routine_code(request.form.get('routine_code'))
    if len(routine_code) != 6:
        flash('Le code routine doit contenir 6 chiffres.', 'error')
        return redirect(url_for('hr.personnel', user_id=user.id))
    user.routine_code = routine_code
    db.session.commit()
    flash('Code routine mis a jour.', 'success')
    return redirect(url_for('hr.personnel', user_id=user.id))


@hr_bp.route('/personnel/photo/<int:user_id>')
@login_required
def personnel_photo(user_id):
    photo = UserPhoto.query.filter_by(user_id=user_id).first_or_404()
    return Response(photo.image_data, mimetype=photo.mime_type)


@hr_bp.route('/personnel/photo', methods=['POST'])
@login_required
def save_personnel_photo():
    user_id = int(request.form['user_id'])
    uploaded = request.files.get('photo')
    if not uploaded or not uploaded.filename:
        flash('Aucune photo selectionnee.', 'error')
        return redirect(url_for('hr.personnel', user_id=user_id))
    if uploaded.mimetype not in ALLOWED_PHOTO_TYPES:
        flash('Format photo accepte : JPG, PNG ou WEBP.', 'error')
        return redirect(url_for('hr.personnel', user_id=user_id))
    data = uploaded.read()
    if len(data) > 2 * 1024 * 1024:
        flash('Photo trop lourde : maximum 2 Mo.', 'error')
        return redirect(url_for('hr.personnel', user_id=user_id))
    photo = UserPhoto.query.filter_by(user_id=user_id).first()
    if not photo:
        photo = UserPhoto(user_id=user_id, filename=uploaded.filename, mime_type=uploaded.mimetype, image_data=data)
        db.session.add(photo)
    else:
        photo.filename = uploaded.filename
        photo.mime_type = uploaded.mimetype
        photo.image_data = data
    db.session.commit()
    flash('Photo mise a jour.', 'success')
    return redirect(url_for('hr.personnel', user_id=user_id))


@hr_bp.route('/personnel/horaires-semaine', methods=['POST'])
@login_required
def save_user_week_schedule():
    user_id = int(request.form['user_id'])
    WeeklyUserSchedule.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    for weekday in range(7):
        if not request.form.get(f'active_{weekday}'):
            continue
        start_time = parse_time(request.form.get(f'start_{weekday}'))
        end_time = parse_time(request.form.get(f'end_{weekday}'))
        if not start_time or not end_time or end_time <= start_time:
            flash(f'Horaire invalide pour {WEEKDAYS[weekday]}.', 'error')
            db.session.rollback()
            return redirect(url_for('hr.personnel', user_id=user_id))
        item = WeeklyUserSchedule(user_id=user_id, weekday=weekday, start_time=start_time, end_time=end_time, status=request.form.get(f'status_{weekday}', 'present'), note=request.form.get(f'note_{weekday}', ''))
        db.session.add(item)
    db.session.commit()
    flash('Horaires de base de la semaine enregistres.', 'success')
    return redirect(url_for('hr.personnel', user_id=user_id))


@hr_bp.route('/personnel/horaires-base', methods=['POST'])
@login_required
def add_user_base_schedule():
    start_time = parse_time(request.form.get('start_time'))
    end_time = parse_time(request.form.get('end_time'))
    if not start_time or not end_time or end_time <= start_time:
        flash('Horaire salarie invalide.', 'error')
        return redirect(url_for('hr.personnel'))
    item = WeeklyUserSchedule(user_id=int(request.form['user_id']), weekday=int(request.form['weekday']), start_time=start_time, end_time=end_time, status=request.form.get('status', 'present'), note=request.form.get('note', ''))
    db.session.add(item)
    db.session.commit()
    flash('Horaire de base ajoute.', 'success')
    return redirect(url_for('hr.personnel'))


@hr_bp.route('/personnel/horaires-base/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_user_base_schedule(item_id):
    item = WeeklyUserSchedule.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Horaire de base supprime.', 'success')
    return redirect(url_for('hr.personnel'))


@hr_bp.route('/personnel/dispos-cabines-base', methods=['POST'])
@login_required
def add_cabin_base_schedule():
    start_time = parse_time(request.form.get('start_time'))
    end_time = parse_time(request.form.get('end_time'))
    if not start_time or not end_time or end_time <= start_time:
        flash('Disponibilite cabine invalide.', 'error')
        return redirect(url_for('hr.personnel'))
    item = WeeklyCabinSchedule(cabin_id=int(request.form['cabin_id']), weekday=int(request.form['weekday']), start_time=start_time, end_time=end_time, status=request.form.get('status', 'available'), note=request.form.get('note', ''))
    db.session.add(item)
    db.session.commit()
    flash('Disponibilite cabine de base ajoutee.', 'success')
    return redirect(url_for('hr.personnel'))


@hr_bp.route('/personnel/dispos-cabines-base/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_cabin_base_schedule(item_id):
    item = WeeklyCabinSchedule.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Disponibilite cabine de base supprimee.', 'success')
    return redirect(url_for('hr.personnel'))


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