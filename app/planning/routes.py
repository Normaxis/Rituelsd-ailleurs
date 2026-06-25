from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import User, WorkSlot, Appointment, Cabin
from app.utils.auth import login_required

planning_bp = Blueprint('planning', __name__)

@planning_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        work_date = datetime.strptime(request.form['work_date'], '%Y-%m-%d').date()
        ws = WorkSlot(user_id=int(request.form['user_id']), work_date=work_date, start_time=datetime.strptime(request.form['start_time'], '%H:%M').time(), end_time=datetime.strptime(request.form['end_time'], '%H:%M').time(), status=request.form.get('status', 'present'), note=request.form.get('note', ''))
        db.session.add(ws)
        db.session.commit()
        return redirect(url_for('planning.index', date=work_date.isoformat()))

    selected = request.args.get('date')
    selected_date = datetime.strptime(selected, '%Y-%m-%d').date() if selected else date.today()
    start_day = datetime.combine(selected_date, datetime.min.time())
    end_day = start_day + timedelta(days=1)
    users = User.query.order_by(User.first_name, User.last_name).all()
    cabins = Cabin.query.filter_by(is_active=True).order_by(Cabin.name).all()
    slots = WorkSlot.query.filter_by(work_date=selected_date).all()
    appointments = Appointment.query.filter(Appointment.start_at >= start_day, Appointment.start_at < end_day).order_by(Appointment.start_at).all()
    hours = list(range(8, 21))
    return render_template('planning/pro.html', users=users, cabins=cabins, slots=slots, appointments=appointments, selected_date=selected_date, prev_day=selected_date - timedelta(days=1), next_day=selected_date + timedelta(days=1), hours=hours)
