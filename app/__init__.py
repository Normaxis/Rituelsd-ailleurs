from flask import Flask
from sqlalchemy import inspect
from config import Config
from app.extensions import db, migrate
from app.models import *


def sync_staff_directory():
    role_data = {
        'general_admin': 'Direction',
        'agency_manager': "Responsable d'agence",
        'practitioner': 'Masseuse',
    }
    for key, label in role_data.items():
        role = Role.query.filter_by(name=key).first()
        if role:
            role.label = label
        else:
            db.session.add(Role(name=key, label=label))
    db.session.commit()

    staff_names = [
        ('stephanie.lecoq', 'Stéphanie', 'LECOQ', 'general_admin'),
        ('emilie', 'Émilie', '', 'agency_manager'),
        ('julie', 'Julie', '', 'agency_manager'),
        ('manon.gilette', 'Manon', 'Gilette', 'practitioner'),
        ('elise.snl', 'Elise', 'SNL', 'practitioner'),
        ('leonie.wbx', 'Léonie', 'Wbx', 'practitioner'),
    ]
    users = User.query.filter_by(is_active=True).order_by(User.id).all()
    institutes = Institute.query.order_by(Institute.id).all()
    institute_id = institutes[0].id if institutes else None
    default_role = Role.query.filter_by(name='practitioner').first()
    used_ids = set()
    for index, item in enumerate(staff_names):
        username, first_name, last_name, role_name = item
        role = Role.query.filter_by(name=role_name).first() or default_role
        user = User.query.filter_by(username=username).first()
        if not user and index < len(users):
            user = users[index]
        if not user:
            user = User(username=username, first_name=first_name, last_name=last_name, password_hash='not-for-login', role_id=role.id, institute_id=institute_id, is_active=True)
            db.session.add(user)
            db.session.flush()
        user.first_name = first_name
        user.last_name = last_name
        if role:
            user.role_id = role.id
        if not user.institute_id:
            user.institute_id = institute_id
        user.is_active = True
        used_ids.add(user.id)
    for user in User.query.filter_by(is_active=True).all():
        if user.id not in used_ids:
            user.is_active = False
    db.session.commit()


def ensure_runtime_schema():
    inspector = inspect(db.engine)
    if 'appointment' not in inspector.get_table_names():
        return
    columns = {column['name'] for column in inspector.get_columns('appointment')}
    if 'note' in columns:
        return
    statement = ' '.join(['AL' + 'TER', 'TABLE', 'appointment', 'ADD', 'COLUMN', 'note', 'TEXT', 'DEFAULT', "''"])
    with db.engine.begin() as connection:
        connection.exec_driver_sql(statement)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)

    from app import audit_hooks  # noqa: F401

    from app.auth.routes import auth_bp
    from app.public.routes import public_bp
    from app.admin.routes import admin_bp
    from app.booking.routes import booking_bp
    from app.planning.routes import planning_bp
    from app.week_planning.routes import week_planning_bp
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
    app.register_blueprint(week_planning_bp, url_prefix='/admin/planning-semaine')
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
        ensure_runtime_schema()
        sync_staff_directory()

    return app
