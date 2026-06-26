from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Routine, Cabin
from app.utils.auth import login_required

routines_bp = Blueprint('routines', __name__)

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
    return render_template('routines/index.html', routines=Routine.query.order_by(Routine.name).all(), cabins=Cabin.query.order_by(Cabin.name).all())