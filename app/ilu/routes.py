from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from app.models import User, Treatment, SkillILU
from app.utils.auth import login_required

ilu_bp = Blueprint('ilu', __name__)

@ilu_bp.route('/', methods=['GET','POST'])
@login_required
def matrix():
    users = User.query.all()
    treatments = Treatment.query.all()
    if request.method == 'POST':
        for user in users:
            for treatment in treatments:
                level = request.form.get(f'level_{user.id}_{treatment.id}', '')
                skill = SkillILU.query.filter_by(user_id=user.id, treatment_id=treatment.id).first()
                if not skill:
                    skill = SkillILU(user_id=user.id, treatment_id=treatment.id)
                    db.session.add(skill)
                skill.level = level
        db.session.commit()
        return redirect(url_for('ilu.matrix'))
    skills = {(s.user_id, s.treatment_id): s.level for s in SkillILU.query.all()}
    return render_template('ilu/matrix.html', users=users, treatments=treatments, skills=skills)
