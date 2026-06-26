from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import Product, Supplier, SupplierOrder, SupplierOrderLine
from app.utils.auth import login_required

suppliers_bp = Blueprint('suppliers', __name__)

def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date() if value else None

@suppliers_bp.route('/', methods=['GET','POST'])
@login_required
def index():
    if request.method == 'POST':
        supplier = Supplier(name=request.form['name'], contact_name=request.form.get('contact_name',''), email=request.form.get('email',''), phone=request.form.get('phone',''), address=request.form.get('address',''), notes=request.form.get('notes',''))
        db.session.add(supplier)
        db.session.commit()
        return redirect(url_for('suppliers.index'))
    suppliers = Supplier.query.order_by(Supplier.name).all()
    orders = SupplierOrder.query.order_by(SupplierOrder.created_at.desc()).limit(8).all()
    return render_template('suppliers/index.html', suppliers=suppliers, orders=orders)

@suppliers_bp.route('/commandes', methods=['GET','POST'])
@login_required
def orders():
    if request.method == 'POST':
        order = SupplierOrder(supplier_id=int(request.form['supplier_id']), reference=request.form.get('reference',''), order_date=parse_date(request.form.get('order_date')), expected_date=parse_date(request.form.get('expected_date')), status=request.form.get('status','draft'), total_amount=float(request.form.get('total_amount') or 0), notes=request.form.get('notes',''))
        db.session.add(order)
        db.session.commit()
        return redirect(url_for('suppliers.orders'))
    return render_template('suppliers/orders.html', orders=SupplierOrder.query.order_by(SupplierOrder.created_at.desc()).all(), suppliers=Supplier.query.order_by(Supplier.name).all())

@suppliers_bp.route('/commandes/<int:order_id>', methods=['GET','POST'])
@login_required
def order_detail(order_id):
    order = SupplierOrder.query.get_or_404(order_id)
    if request.method == 'POST':
        line = SupplierOrderLine(order_id=order.id, product_id=int(request.form['product_id']) if request.form.get('product_id') else None, label=request.form.get('label',''), quantity=float(request.form.get('quantity') or 0), unit_price=float(request.form.get('unit_price') or 0))
        db.session.add(line)
        order.total_amount = sum(l.line_total for l in order.lines) + line.line_total
        db.session.commit()
        return redirect(url_for('suppliers.order_detail', order_id=order.id))
    return render_template('suppliers/order_detail.html', order=order, products=Product.query.order_by(Product.name).all())
