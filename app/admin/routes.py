from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Treatment, Cabin, User, AuditLog, Institute, Customer, GiftCard, Supplier, DocumentRecord, QSEAction, Product
from app.utils.auth import login_required, current_user

admin_bp = Blueprint('admin', __name__)

def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None

@admin_bp.route('/')
@login_required
def dashboard():
    return render_template('admin/dashboard.html', treatments=Treatment.query.count(), cabins=Cabin.query.count(), users=User.query.count(), customers=Customer.query.count(), giftcards=GiftCard.query.count(), suppliers=Supplier.query.count(), documents=DocumentRecord.query.count(), qse_actions=QSEAction.query.count(), low_stock=Product.query.filter(Product.quantity <= Product.alert_threshold).count())

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

@admin_bp.route('/documents', methods=['GET','POST'])
@login_required
def documents():
    if request.method == 'POST':
        doc = DocumentRecord(title=request.form['title'], category=request.form.get('category','Procedure'), version=request.form.get('version','1.0'), owner=request.form.get('owner',''), file_url=request.form.get('file_url',''), review_date=parse_date(request.form.get('review_date')))
        db.session.add(doc); db.session.commit()
        return redirect(url_for('admin.documents'))
    return render_template('documents/index.html', docs=DocumentRecord.query.order_by(DocumentRecord.created_at.desc()).all())

@admin_bp.route('/qse')
@login_required
def qse():
    return render_template('admin/module_list.html', title='QSE', subtitle='DUERP, audits, plans d actions, reclamations, presque accidents et environnement.', items=QSEAction.query.order_by(QSEAction.created_at.desc()).all(), columns=['Theme', 'Action', 'Responsable', 'Statut'])

@admin_bp.route('/audit')
@login_required
def audit():
    return render_template('admin/audit.html', logs=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all())
