from flask import Blueprint, redirect, request, url_for

from app.extensions import db
from app.models import RoutineCompletion, RoutineProofPhoto
from app.utils.auth import login_required

routine_proofs_bp = Blueprint('routine_proofs', __name__)
ALLOWED_PHOTO_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_PHOTO_BYTES = 3 * 1024 * 1024


@routine_proofs_bp.route('/admin/routines/preuve/<int:validation_id>', methods=['POST'])
@login_required
def add(validation_id):
    validation = RoutineCompletion.query.get_or_404(validation_id)
    for uploaded in request.files.getlist('proof_photos'):
        if not uploaded or not uploaded.filename or uploaded.mimetype not in ALLOWED_PHOTO_TYPES:
            continue
        data = uploaded.read()
        if not data or len(data) > MAX_PHOTO_BYTES:
            continue
        db.session.add(RoutineProofPhoto(completion_id=validation.id, kind='proof', filename=uploaded.filename, mime_type=uploaded.mimetype, image_data=data))
    note = request.form.get('note') or ''
    if note:
        validation.note = ((validation.note or '') + '\n' + note).strip()
    db.session.commit()
    return redirect(url_for('routines.report', validation_id=validation.id))
