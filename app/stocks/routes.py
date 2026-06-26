from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import Product, StockMovement, Treatment, TreatmentConsumption
from app.utils.auth import login_required

stocks_bp = Blueprint('stocks', __name__)


def _latest_unit_costs(products):
    costs = {}
    for product in products:
        movement = StockMovement.query.filter(
            StockMovement.product_id == product.id,
            StockMovement.unit_cost > 0,
        ).order_by(StockMovement.created_at.desc()).first()
        costs[product.id] = movement.unit_cost if movement else 0
    return costs


def _stock_status(product):
    quantity = product.quantity or 0
    threshold = product.alert_threshold or 0
    if threshold <= 0:
        return 'watch', 'Seuil non defini'
    if quantity <= 0:
        return 'out', 'Rupture'
    if quantity <= threshold:
        return 'alert', 'A recommander'
    if quantity <= threshold * 1.5:
        return 'watch', 'A surveiller'
    return 'ok', 'OK'


def _stock_rows(products, costs, consumptions_by_product):
    rows = []
    for product in products:
        status_class, status_label = _stock_status(product)
        unit_cost = costs.get(product.id, 0) or 0
        quantity = product.quantity or 0
        threshold = product.alert_threshold or 0
        stock_value = quantity * unit_cost
        coverage_ratio = None
        if threshold > 0:
            coverage_ratio = round(quantity / threshold, 1)
        rows.append({
            'product': product,
            'unit_cost': unit_cost,
            'stock_value': stock_value,
            'status_class': status_class,
            'status_label': status_label,
            'coverage_ratio': coverage_ratio,
            'consumption_count': consumptions_by_product.get(product.id, 0),
        })
    return rows


@stocks_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        p = Product(name=request.form['name'], unit=request.form['unit'], quantity=float(request.form['quantity'] or 0), alert_threshold=float(request.form['alert_threshold'] or 0))
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('stocks.index'))

    products = Product.query.order_by(Product.name).all()
    low_products = [p for p in products if (p.quantity or 0) <= (p.alert_threshold or 0)]
    movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(12).all()
    recent_start = datetime.utcnow() - timedelta(days=30)
    recent_movements = StockMovement.query.filter(StockMovement.created_at >= recent_start).all()
    consumptions = TreatmentConsumption.query.all()
    consumption_product_ids = {item.product_id for item in consumptions}
    consumption_treatment_ids = {item.treatment_id for item in consumptions}
    active_treatments_count = Treatment.query.filter_by(is_active=True).count()
    consumptions_by_product = {}
    for item in consumptions:
        consumptions_by_product[item.product_id] = consumptions_by_product.get(item.product_id, 0) + 1

    costs = _latest_unit_costs(products)
    stock_rows = _stock_rows(products, costs, consumptions_by_product)
    stock_value = sum(row['stock_value'] for row in stock_rows)
    products_without_consumption = [p for p in products if p.id not in consumption_product_ids]
    treatment_coverage = round((len(consumption_treatment_ids) / active_treatments_count) * 100) if active_treatments_count else 0
    recent_entries = sum(m.quantity or 0 for m in recent_movements if (m.quantity or 0) > 0)
    recent_outputs = abs(sum(m.quantity or 0 for m in recent_movements if (m.quantity or 0) < 0))
    recent_losses = abs(sum(m.quantity or 0 for m in recent_movements if m.movement_type == 'loss'))
    reorder_priority = [row for row in stock_rows if row['status_class'] in ['out', 'alert', 'watch']]

    return render_template(
        'stocks/index.html',
        products=products,
        low_products=low_products,
        movements=movements,
        stock_rows=stock_rows,
        stock_value=stock_value,
        recent_entries=recent_entries,
        recent_outputs=recent_outputs,
        recent_losses=recent_losses,
        products_without_consumption=products_without_consumption,
        treatment_coverage=treatment_coverage,
        active_treatments_count=active_treatments_count,
        reorder_priority=reorder_priority,
    )


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
        treatment_id = int(request.form['treatment_id'])
        product_id = int(request.form['product_id'])
        quantity = float(request.form.get('quantity') or 0)
        item = TreatmentConsumption.query.filter_by(treatment_id=treatment_id, product_id=product_id).first()
        if item:
            item.quantity = quantity
            flash('Consommation existante mise a jour.', 'success')
        else:
            item = TreatmentConsumption(treatment_id=treatment_id, product_id=product_id, quantity=quantity)
            db.session.add(item)
            flash('Consommation ajoutee.', 'success')
        db.session.commit()
        return redirect(url_for('stocks.consumptions'))
    items = TreatmentConsumption.query.all()
    treatments = Treatment.query.filter_by(is_active=True).order_by(Treatment.name).all()
    products = Product.query.order_by(Product.name).all()
    configured_treatment_ids = {item.treatment_id for item in items}
    configured_product_ids = {item.product_id for item in items}
    return render_template(
        'stocks/consumptions.html',
        items=items,
        treatments=treatments,
        products=products,
        configured_treatment_ids=configured_treatment_ids,
        configured_product_ids=configured_product_ids,
    )
