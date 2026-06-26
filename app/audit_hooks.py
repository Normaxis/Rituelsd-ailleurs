from flask import has_request_context, request, session
from sqlalchemy import event, inspect

from app.models import Appointment, AuditLog, WorkSlot


PLANNING_PREFIX = '/admin/planning'


def _planning_request():
    return has_request_context() and request.path.startswith(PLANNING_PREFIX)


def _current_user_id():
    if not has_request_context():
        return None
    return session.get('user_id')


def _insert_audit(connection, action):
    if not _planning_request():
        return
    connection.execute(
        AuditLog.__table__.insert().values(
            user_id=_current_user_id(),
            module='planning',
            action=action,
        )
    )


def _changed(target, fields):
    state = inspect(target)
    return any(state.attrs[field].history.has_changes() for field in fields if field in state.attrs)


@event.listens_for(Appointment, 'after_insert')
def audit_appointment_created(mapper, connection, target):
    _insert_audit(
        connection,
        (
            f"Creation RDV #{target.id} - {target.customer_name} - "
            f"prestation {target.treatment_id} - praticienne {target.user_id} - "
            f"cabine {target.cabin_id} - {target.start_at:%d/%m/%Y %H:%M}"
        ),
    )


@event.listens_for(Appointment, 'after_update')
def audit_appointment_updated(mapper, connection, target):
    if _changed(target, ['start_at', 'end_at', 'user_id', 'cabin_id', 'status']):
        _insert_audit(
            connection,
            (
                f"Modification RDV #{target.id} - {target.customer_name} - "
                f"statut {target.status} - praticienne {target.user_id} - "
                f"cabine {target.cabin_id} - {target.start_at:%d/%m/%Y %H:%M}"
            ),
        )


@event.listens_for(WorkSlot, 'after_insert')
def audit_workslot_created(mapper, connection, target):
    _insert_audit(
        connection,
        (
            f"Creation creneau planning #{target.id} - praticienne {target.user_id} - "
            f"{target.work_date:%d/%m/%Y} {target.start_time:%H:%M}-{target.end_time:%H:%M} - {target.status}"
        ),
    )


@event.listens_for(WorkSlot, 'after_update')
def audit_workslot_updated(mapper, connection, target):
    if _changed(target, ['user_id', 'work_date', 'start_time', 'end_time', 'status']):
        _insert_audit(
            connection,
            (
                f"Modification creneau planning #{target.id} - praticienne {target.user_id} - "
                f"{target.work_date:%d/%m/%Y} {target.start_time:%H:%M}-{target.end_time:%H:%M} - {target.status}"
            ),
        )
