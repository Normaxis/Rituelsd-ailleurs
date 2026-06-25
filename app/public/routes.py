from flask import Blueprint, render_template
from app.models import Treatment, Institute

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def home():
    return render_template('public/home.html', treatments=Treatment.query.filter_by(is_active=True).all(), institutes=Institute.query.all())

@public_bp.route('/prestations')
def treatments():
    return render_template('public/treatments.html', treatments=Treatment.query.filter_by(is_active=True).all())
