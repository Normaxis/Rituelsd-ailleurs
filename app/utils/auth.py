from functools import wraps
from flask import session, redirect, url_for, abort
from app.models import User

def current_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('auth.login'))
            if session.get('role') not in roles and session.get('role') != 'general_admin':
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco
