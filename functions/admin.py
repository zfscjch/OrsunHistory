from flask import Blueprint, render_template, request, abort, Response, g
from .api_response import api_response
from .error_handlers import get_all, resolve_error
from .config import Config

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
def check_admin():
    auth = request.authorization
    if not auth:
        return Response('需要认证', 401,
                        {'WWW-Authenticate': 'Basic realm="Admin Panel"'})
    username = auth.username
    password = auth.password
    if not username or not password:
        return Response('需要认证', 401,
                        {'WWW-Authenticate': 'Basic realm="Admin Panel"'})
    elif username != "admin" or password != Config.MASTER_PASSWORD:
        abort(403)
    return None


@admin_bp.route("/")
def get_index():
    return render_template("admin.html")


@admin_bp.route("/maintenance")
def get_maintenance():
    return render_template("maintenance.html")


@admin_bp.route("/check-issues")
def get_issues_html():
    return render_template("show_issues.html")


@admin_bp.route("/get-issues")
def get_issues():
    status, data, code = get_all()
    return api_response(status, data=data, http_code=code)


@admin_bp.route("/resolve-issues", methods=["POST"])
def resolve_issues():
    if not request.is_json:
        return api_response("error", "请求必须为 JSON", http_code=400)

    data = request.get_json()
    if not "error_id" in data:
        return api_response("error", "缺少error_id字段")

    error_id = data["error_id"]
    status, msg, code = resolve_error(error_id)
    return api_response(status, msg, http_code=code)

@admin_bp.route("/get-log")
def get_log():
    log_mgr = g.log_mgr
    data = log_mgr.get_log().replace("\n", "<br>")
    return render_template("log.html", data=data)
