from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Product, StockMovement, Treatment, TreatmentConsumption
from app.utils.auth import login_required

stocks_bp = Blueprint('stocks', __name__)

@stocks_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        p = Product(name=request.form['name'], unit=request.form['unit'], quantity=float(request.form['quantity']), alert_threshold=float(request.form['alert_threshold']))
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('stocks.index'))
    products = Product.query.order_by(Product.name).all()
    low_products = [p for p in products if p.quantity <= p.alert_threshold]
    movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(12).all()
    return render_template('stocks/index.html', products=products, low_products=low_products, movements=movements)

@stocks_bp.route('/mouvement', methods=['POST'])
@login_required
def movement():
    product = Product.query.get_or_404(int(request.form['product_id']))
    movement_type = request.form.get('movement_type','adjustment')
    quantity = float(request.form.get('quantity') or 0)
    if movement_type in ['out', 'loss']:
        quantity = -abs(quantity)
    else:
        quantity = abs(quantity)
    product.quantity = (product.quantity or 0) + quantity
    m = StockMovement(product_id=product.id, movement_type=movement_type, quantity=quantity, unit_cost=float(request.form.get('unit_cost') or 0), reason=request.form.get('reason',''))
    db.session.add(m)
    db.session.commit()
    return redirect(url_for('stocks.index'))

@stocks_bp.route('/consommations', methods=['GET','POST'])
@login_required
def consumptions():
    if request.method == 'POST':
        item = TreatmentConsumption(treatment_id=int(request.form['treatment_id']), product_id=int(request.form['product_id']), quantity=float(request.form.get('quantity') or 0))
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('stocks.consumptions'))
    return render_template('stocks/consumptions.html', items=TreatmentConsumption.query.all(), treatments=Treatment.query.filter_by(is_active=True).order_by(Treatment.name).all(), products=Product.query.order_by(Product.name).all())
