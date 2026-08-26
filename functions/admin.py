from flask import Blueprint, render_template, request, g
from .api_response import api_response, request_not_json_res, request_miss_arg_res, server_error_res
from .error_handlers import get_all, resolve_error
from .decorators import admin_required
from .config import Config

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/")
@admin_required
def get_index():
    return render_template("admin.html")

@admin_bp.route("/maintenance")
@admin_required
def get_maintenance():
    return render_template("maintenance.html")

@admin_bp.route("/check-issues")
@admin_required
def get_issues_html():
    return render_template("show_issues.html")

@admin_bp.route("/get-issues")
@admin_required
def get_issues():
    status, data, code = get_all()
    return api_response(status, data=data, http_code=code)

@admin_bp.route("/resolve-issues", methods=["POST"])
@admin_required
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
@admin_required
def get_log():
    log_mgr = g.log_mgr
    data = log_mgr.get_log().replace("\n", "<br>")
    return render_template("log.html", data=data)

@admin_bp.route("/check", methods=["POST"])
def post_check_admin():
    return api_response("error", "此接口已弃用", http_code=410)

@admin_bp.route("/get-draft")
@admin_required
def get_all_drafts():
    students_mgr = g.students_mgr
    student_data, code_stu = students_mgr.get_draft()
    if code_stu == 200:
        return api_response("success", "", {"a": student_data})
    return api_response("error", student_data, http_code=500)

@admin_bp.route("/change-status", methods=["POST"])
@admin_required
def update_maintenance():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not "m" in data:
            return request_miss_arg_res()

        maintenance_mode = bool(data["m"])
        Config.set_maintenance(maintenance_mode)
        return api_response("success", f"服务器是否维护：{'是' if maintenance_mode else '否'}")
    except Exception as e:
        return server_error_res("更新maintenance", e)