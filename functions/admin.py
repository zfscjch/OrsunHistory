import mysql.connector
from flask import Blueprint, render_template, request, abort, Response, g
from .api_response import api_response, request_not_json_res, request_miss_arg_res, server_error_res
from .error_handlers import get_all, resolve_error
from .config import Config

admin_bp = Blueprint("admin", __name__)

def check_admins(user_id):
    with mysql.connector.connect(**Config.MySQLConfig) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT is_admin FROM users WHERE id = %s", (str(user_id),))
            is_admin = cursor.fetchone()
            return is_admin

@admin_bp.before_request
def check_admin():
    allow_paths = ["/admin/check", "/admin/get-draft"]
    if request.path in allow_paths:
        return None

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
        return request_not_json_res()

    data = request.get_json()
    if not "error_id" in data:
        return request_miss_arg_res()

    error_id = data["error_id"]
    status, msg, code = resolve_error(error_id)
    return api_response(status, msg, http_code=code)

@admin_bp.route("/get-log")
def get_log():
    log_mgr = g.log_mgr
    data = log_mgr.get_log().replace("\n", "<br>")
    return render_template("log.html", data=data)

@admin_bp.route("/check", methods=["POST"])
def post_check_admin():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not 'userID' in data:
            return request_miss_arg_res()

        user_id = data["userID"]
        res = check_admins(user_id)
        return api_response("success", "", {"isAdmin": res})
    except Exception as e:
        return server_error_res("检查用户是否为管理员", e)

@admin_bp.route("/get-draft")
def get_all_drafts():
    students_mgr = g.students_mgr
    student_data, code_stu = students_mgr.get_draft()
    if code_stu == 200:
        return api_response("success", "", {"a": student_data})
    return api_response("error", student_data, http_code=500)

@admin_bp.route("/change-status", methods=["POST"])
def update_maintenance():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not "m" in data:
            return request_miss_arg_res()

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
            return api_response("error", "用户名或密码错误", http_code=403)

        maintenance_mode = bool(data["m"])
        Config.set_maintenance(maintenance_mode)
        return api_response("success", f"服务器是否维护：{'是' if maintenance_mode else '否'}")
    except Exception as e:
        return server_error_res("更新maintenance", e)