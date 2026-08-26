from functools import wraps
from flask import session, request, redirect
from .api_response import api_response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.method == "POST":
                return api_response("error", "请先登录", http_code=401)
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return api_response('error', "请先登录", http_code=401)
        is_admin = session['is_admin']
        if not is_admin:
            return api_response("error", "需要管理员权限", http_code=403)
        return f(*args, **kwargs)
    return decorated_function