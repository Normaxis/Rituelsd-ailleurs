from flask import Flask
from config import Config
from app.extensions import db
from app.models import *


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    from app.auth.routes import auth_bp
    from app.public.routes import public_bp
    from app.admin.routes import admin_bp
    from app.booking.routes import booking_bp
    from app.planning.routes import planning_bp
    from app.ilu.routes import ilu_bp
    from app.stocks.routes import stocks_bp
    from app.routines.routes import routines_bp
    from app.hr.routes import hr_bp
    from app.customers.routes import customers_bp
    from app.giftcards.routes import giftcards_bp
    from app.suppliers.routes import suppliers_bp
    from app.appointments.routes import appointments_bp
    from app.waitlist.routes import waitlist_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(booking_bp, url_prefix='/reservation')
    app.register_blueprint(planning_bp, url_prefix='/admin/planning')
    app.register_blueprint(ilu_bp, url_prefix='/admin/ilu')
    app.register_blueprint(stocks_bp, url_prefix='/admin/stocks')
    app.register_blueprint(routines_bp, url_prefix='/admin/routines')
    app.register_blueprint(hr_bp, url_prefix='/admin/rh')
    app.register_blueprint(customers_bp, url_prefix='/admin/clients')
    app.register_blueprint(giftcards_bp, url_prefix='/admin/cartes-cadeaux')
    app.register_blueprint(suppliers_bp, url_prefix='/admin/fournisseurs')
    app.register_blueprint(appointments_bp, url_prefix='/admin/rendez-vous')
    app.register_blueprint(waitlist_bp)

    with app.app_context():
        db.create_all()

    return app
