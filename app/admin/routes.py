from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Treatment, Cabin, User, AuditLog, Institute, DocumentRecord, QSEAction, Product, Customer, GiftCard, Supplier, Appointment, HabilitationRecord, TrainingRecord
from app.utils.auth import login_required, current_user

admin_bp = Blueprint('admin', __name__)

def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None

@admin_bp.route('/')
@login_required
def dashboard():
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)
    soon = today + timedelta(days=60)
    today_appointments = Appointment.query.filter(Appointment.start_at >= start, Appointment.start_at < end).order_by(Appointment.start_at).all()
    today_revenue = sum(a.treatment.price or 0 for a in today_appointments if a.status != 'cancelled')
    low_stock = Product.query.filter(Product.quantity <= Product.alert_threshold).count()
    giftcards_expiring = GiftCard.query.filter(GiftCard.expires_on != None, GiftCard.expires_on <= soon, GiftCard.status == 'active').count()
    habilitations_due = HabilitationRecord.query.filter(HabilitationRecord.expires_on != None, HabilitationRecord.expires_on <= soon).count()
    trainings_due = TrainingRecord.query.filter(TrainingRecord.expires_on != None, TrainingRecord.expires_on <= soon).count()
    open_qse = QSEAction.query.filter(QSEAction.status != 'closed').count()
    late_qse = QSEAction.query.filter(QSEAction.status != 'closed', QSEAction.due_date != None, QSEAction.due_date < today).count()
    return render_template('admin/dashboard.html', treatments=Treatment.query.count(), cabins=Cabin.query.count(), users=User.query.count(), customers=Customer.query.count(), giftcards=GiftCard.query.count(), suppliers=Supplier.query.count(), documents=DocumentRecord.query.count(), qse_actions=QSEAction.query.count(), low_stock=low_stock, today_appointments=today_appointments, today_revenue=today_revenue, giftcards_expiring=giftcards_expiring, habilitations_due=habilitations_due, trainings_due=trainings_due, open_qse=open_qse, late_qse=late_qse)

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
        item = DocumentRecord(title=request.form['title'], category=request.form.get('category','Procedure'), version=request.form.get('version','1.0'), owner=request.form.get('owner',''), file_url=request.form.get('file_url',''), review_date=parse_date(request.form.get('review_date')))
        db.session.add(item); db.session.commit()
        return redirect(url_for('admin.documents'))
    return render_template('admin/module_list.html', title='Documents', subtitle='Procedures, modes operatoires, DUERP, audits et versionnage documentaire.', items=DocumentRecord.query.order_by(DocumentRecord.created_at.desc()).all(), columns=['Titre','Categorie','Version','Revue'])

@admin_bp.route('/qse', methods=['GET','POST'])
@login_required
def qse():
    if request.method == 'POST':
        item = QSEAction(source=request.form.get('source','Audit'), theme=request.form.get('theme','Securite'), title=request.form['title'], description=request.form.get('description',''), responsible=request.form.get('responsible',''), due_date=parse_date(request.form.get('due_date')), status=request.form.get('status','open'))
        db.session.add(item); db.session.commit()
        return redirect(url_for('admin.qse'))
    actions = QSEAction.query.order_by(QSEAction.created_at.desc()).all()
    open_actions = [a for a in actions if a.status != 'closed']
    late_actions = [a for a in open_actions if a.due_date and a.due_date < datetime.today().date()]
    return render_template('qse/index.html', actions=actions, open_actions=open_actions, late_actions=late_actions)

@admin_bp.route('/audit')
@login_required
def audit():
    return render_template('admin/audit.html', logs=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all())
