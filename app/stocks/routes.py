from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Product
from app.utils.auth import login_required

stocks_bp = Blueprint('stocks', __name__)

@stocks_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        p = Product(name=request.form['name'], unit=request.form['unit'], quantity=float(request.form['quantity']), alert_threshold=float(request.form['alert_threshold']))
        db.session.add(p); db.session.commit()
        return redirect(url_for('stocks.index'))
    return render_template('stocks/index.html', products=Product.query.all())
