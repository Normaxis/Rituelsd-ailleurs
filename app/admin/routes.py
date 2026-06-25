from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Treatment, Cabin, User, AuditLog, Institute
from app.utils.auth import login_required, current_user

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
def dashboard():
    return render_template('admin/dashboard.html', treatments=Treatment.query.count(), cabins=Cabin.query.count(), users=User.query.count())

@admin_bp.route('/prestations', methods=['GET','POST'])
@login_required
def treatments():
    if request.method == 'POST':
        t = Treatment(name=request.form['name'], category=request.form['category'], duration_minutes=int(request.form['duration']), price=float(request.form['price']), institute_id=int(request.form['institute_id']))
        db.session.add(t); db.session.commit()
        return redirect(url_for('admin.treatments'))
    return render_template('admin/treatments.html', treatments=Treatment.query.all(), institutes=Institute.query.all())

@admin_bp.route('/prestations/<int:item_id>/delete', methods=['POST'])
@login_required
def treatment_delete(item_id):
    item = Treatment.query.get_or_404(item_id); db.session.delete(item); db.session.commit()
    return redirect(url_for('admin.treatments'))

@admin_bp.route('/cabines', methods=['GET','POST'])
@login_required
def cabins():
    if request.method == 'POST':
        c = Cabin(name=request.form['name'], cabin_type=request.form['cabin_type'], institute_id=int(request.form['institute_id']))
        db.session.add(c); db.session.commit()
        return redirect(url_for('admin.cabins'))
    return render_template('admin/cabins.html', cabins=Cabin.query.all(), institutes=Institute.query.all())

@admin_bp.route('/audit')
@login_required
def audit():
    return render_template('admin/audit.html', logs=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all())
