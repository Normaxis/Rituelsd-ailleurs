from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import DocumentRecord
from app.utils.auth import login_required

documents_bp = Blueprint('documents', __name__)

def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None

@documents_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        doc = DocumentRecord(title=request.form['title'], category=request.form.get('category','Procedure'), version=request.form.get('version','1.0'), owner=request.form.get('owner',''), file_url=request.form.get('file_url',''), review_date=parse_date(request.form.get('review_date')))
        db.session.add(doc)
        db.session.commit()
        return redirect(url_for('documents.index'))
    docs = DocumentRecord.query.order_by(DocumentRecord.created_at.desc()).all()
    return render_template('documents/index.html', docs=docs)
