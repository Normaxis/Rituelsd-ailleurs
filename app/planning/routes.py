from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import User, WorkSlot, Appointment
from app.utils.auth import login_required

planning_bp = Blueprint('planning', __name__)

@planning_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        ws = WorkSlot(user_id=int(request.form['user_id']), work_date=datetime.strptime(request.form['work_date'],'%Y-%m-%d').date(), start_time=datetime.strptime(request.form['start_time'],'%H:%M').time(), end_time=datetime.strptime(request.form['end_time'],'%H:%M').time(), status=request.form.get('status','present'), note=request.form.get('note',''))
        db.session.add(ws); db.session.commit()
        return redirect(url_for('planning.index'))
    selected = request.args.get('date')
    selected_date = datetime.strptime(selected, '%Y-%m-%d').date() if selected else date.today()
    users = User.query.all()
    slots = WorkSlot.query.filter_by(work_date=selected_date).all()
    appointments = Appointment.query.filter(Appointment.start_at >= datetime.combine(selected_date, datetime.min.time()), Appointment.start_at <= datetime.combine(selected_date, datetime.max.time())).all()
    return render_template('planning/index.html', users=users, slots=slots, appointments=appointments, selected_date=selected_date)
