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

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(booking_bp, url_prefix='/reservation')
    app.register_blueprint(planning_bp, url_prefix='/admin/planning')
    app.register_blueprint(ilu_bp, url_prefix='/admin/ilu')
    app.register_blueprint(stocks_bp, url_prefix='/admin/stocks')
    app.register_blueprint(routines_bp, url_prefix='/admin/routines')

    with app.app_context():
        db.create_all()
        seed_database()

    return app


def seed_database():
    from datetime import date, time, timedelta
    if Role.query.first():
        return
    roles = [
        Role(name='general_admin', label='Administratrice générale'),
        Role(name='shop_manager', label='Responsable institut'),
        Role(name='reception', label='Accueil'),
        Role(name='practitioner', label='Masseuse'),
    ]
    db.session.add_all(roles)
    rituels = Institute(name="Rituels d’Ailleurs", address='17 rue des Arsins, Rouen', phone='')
    petit = Institute(name='Le Petit Rituel', address='Rouen', phone='')
    db.session.add_all([rituels, petit])
    db.session.flush()
    admin = User(first_name='Admin', last_name='Générale', username='admin', role=roles[0], institute=rituels)
    admin.set_password('admin123')
    emma = User(first_name='Emma', last_name='Leroy', username='emma', role=roles[3], institute=rituels); emma.set_password('emma123')
    jade = User(first_name='Jade', last_name='Moreau', username='jade', role=roles[3], institute=petit); jade.set_password('jade123')
    sarah = User(first_name='Sarah', last_name='Martin', username='sarah', role=roles[3], institute=rituels); sarah.set_password('sarah123')
    db.session.add_all([admin, emma, jade, sarah])
    t1 = Treatment(name='Massage Californien', category='Massage', duration_minutes=60, price=75, institute=rituels)
    t2 = Treatment(name='Kobido', category='Soin visage', duration_minutes=75, price=95, institute=rituels)
    t3 = Treatment(name='Drainage lymphatique', category='Massage expert', duration_minutes=60, price=90, institute=petit)
    db.session.add_all([t1, t2, t3])
    c1 = Cabin(name='Cabine Lotus', institute=rituels, cabin_type='Massage solo')
    c2 = Cabin(name='Cabine Duo', institute=rituels, cabin_type='Duo')
    c3 = Cabin(name='Cabine Bambou', institute=petit, cabin_type='Massage solo')
    db.session.add_all([c1, c2, c3])
    db.session.flush()
    db.session.add_all([
        SkillILU(user=emma, treatment=t1, level='U'), SkillILU(user=emma, treatment=t2, level='L'),
        SkillILU(user=sarah, treatment=t1, level='L'), SkillILU(user=sarah, treatment=t2, level='I'),
        SkillILU(user=jade, treatment=t3, level='U')
    ])
    today = date.today()
    for i in range(21):
        d = today + timedelta(days=i)
        if d.weekday() < 5:
            db.session.add(WorkSlot(user=emma, work_date=d, start_time=time(9,0), end_time=time(17,0)))
            db.session.add(WorkSlot(user=sarah, work_date=d, start_time=time(10,0), end_time=time(18,0)))
        if d.weekday() in [1,3,5]:
            db.session.add(WorkSlot(user=jade, work_date=d, start_time=time(9,30), end_time=time(16,30)))
    db.session.add(Product(name='Huile neutre', unit='ml', quantity=5000, alert_threshold=500))
    db.session.add(Routine(name='Remise en état cabine', cabin=c1, instructions='Changer les serviettes\nDésinfecter la table\nVérifier les huiles\nPrendre une photo'))
    db.session.commit()
