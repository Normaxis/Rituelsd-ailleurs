from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import User, Treatment, SkillILU, Institute
from app.utils.auth import login_required

ilu_bp = Blueprint('ilu', __name__)

@ilu_bp.route('/', methods=['GET','POST'])
@login_required
def matrix():
    institute_id = request.args.get('institute_id', type=int)
    category = request.args.get('category', '')
    users_query = User.query.order_by(User.first_name, User.last_name)
    treatments_query = Treatment.query.filter_by(is_active=True).order_by(Treatment.category, Treatment.name)
    if institute_id:
        users_query = users_query.filter_by(institute_id=institute_id)
        treatments_query = treatments_query.filter_by(institute_id=institute_id)
    if category:
        treatments_query = treatments_query.filter_by(category=category)
    users = users_query.all()
    treatments = treatments_query.all()
    if request.method == 'POST':
        for user in users:
            for treatment in treatments:
                field_name = 'level_' + str(user.id) + '_' + str(treatment.id)
                level = request.form.get(field_name, '')
                skill = SkillILU.query.filter_by(user_id=user.id, treatment_id=treatment.id).first()
                if not skill:
                    skill = SkillILU(user_id=user.id, treatment_id=treatment.id)
                    db.session.add(skill)
                skill.level = level
        db.session.commit()
        return redirect(url_for('ilu.matrix', institute_id=institute_id or '', category=category))
    skills = {(s.user_id, s.treatment_id): s.level for s in SkillILU.query.all()}
    institutes = Institute.query.order_by(Institute.name).all()
    categories = [c[0] for c in db.session.query(Treatment.category).distinct().order_by(Treatment.category).all() if c[0]]
    return render_template('ilu/matrix.html', users=users, treatments=treatments, skills=skills, institutes=institutes, categories=categories, selected_institute_id=institute_id, selected_category=category)
