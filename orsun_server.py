import os
import re
import traceback
from typing import Literal
from flask import Flask, request, jsonify, abort, render_template, redirect, Response, g
from flask_cors import CORS
from functions import *

app = Flask(__name__)
CORS(app)

user_mgr = UserMgr()
psg_mgr = PsgMgr()
students_mgr = StudentsMgr()
comments_mgr = CommentsMgr()
os.chdir(os.path.dirname(__file__))
psg_reviewer = PsgReviewer()
locker = AccountLocker("functions/db/login_locks.json")
log_mgr = LogMgr("../logs/OrsunHistory/website.log")


@app.errorhandler(503)
def handle_503(error):
    return render_template("503.html"), 503


@app.before_request
def check():
    """检查访问浏览器和服务器是否符合要求"""
    g.log_mgr = log_mgr
    g.psg_mgr = psg_mgr
    g.students_mgr = students_mgr

    # 先禁止IE访问
    user_agent = request.headers.get("User-Agent", "").lower()
    if "msie" in user_agent or "trident" in user_agent:
        return redirect("/not_allow?code=403&isIe=true")

    # 再检测服务器是否正在维护
    if Config.MAINTENANCE_MODE:
        allow_requests = [r"/api/a-login", r"/health", r"/api/admin/maintenance", r"/admin/*"]
        for allow_request in allow_requests:
            if re.match(allow_request, request.path):
                return None

        if request.headers.get("Content-Type") == "application/json":
            return api_response("error", "服务器正在维护，请稍后访问", {"retry-after": 3600}, 503)
        else:
            abort(503)
    return None


@app.route("/login")
def handle_login():
    return render_template("login.html")


@app.route("/")
def get_index():
    return render_template("index.html")


@app.route("/intro")
def get_intro():
    return render_template("introduce.html")


@app.route("/stu")
def get_stu():
    return render_template("students.html")


@app.route("/edit")
def get_edit():
    return render_template("edit.html")


@app.route("/api/login", methods=["POST"])
def login():
    if not request.is_json:
        return api_response("error", "请求必须为json格式", http_code=400)

    data = request.get_json()

    if not "user" in data or not "pwd" in data:
        return api_response("error", "缺少必要字段", http_code=400)

    user = data["user"]
    password = data["pwd"]
    user_id, is_active, msg = user_mgr.authenticate(user, password)

    if user_id:
        log_mgr.info(user, "登录成功", request.remote_addr)
        status, select_msg, code = check_user(user)
        return api_response("success", msg,
            {"user_id": user_id, "isT": 49 <= user_id <= 60 or user_id == 68,
             "isActive": is_active, "error_hint": select_msg})
    else:
        log_mgr.warn(user, "尝试登录账号失败", request.remote_addr)
        return api_response("error", msg)


@app.route("/api/titles", methods=["POST"])
def get_question():
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        if not "request" in data:
            return api_response("error", "缺少request字段", http_code=400)

        if data["request"] == "GET":
            msg, code = load_titles("functions/db/titles.json")
            status: Literal["success", "error"] = "success" if code == 200 else "error"
            return api_response(status, msg, http_code=code)
        elif data["request"] == "POST":
            if not "msg" in data:
                return api_response("error", "缺少msg字段", http_code=400)
            msg ,code = save_data(data, "functions/db/user_answers.json")
            status: Literal["success", "error"] = "success" if code == 200 else "error"
            return api_response(status, msg, http_code=code)
        return api_response("error", f"no such a request named {data['request']}", http_code=400)
    except Exception as e:
        print(f"服务器错误: {str(e)}")
        log_mgr.error("sys", f"防泄漏验证发生错误：{e}", "127.0.0.1")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/not_allow")
def get_error_page():
    http_code = request.args.get("code", default=200, type=int)
    not_allow_ie = request.args.get("isIe", type=bool)
    is_teacher = request.args.get("isT", type=bool)
    time_limit = request.args.get("time", type=bool)
    if time_limit:
        return render_template("runtime_error.html"), 403
    if not not_allow_ie and http_code >= 400:
        abort(http_code)
    if is_teacher:
        abort(403, description="您的请求被翱三通史管理程序拦截：\n" +
        "检测到您的身份为老师。很抱歉，翱三通史暂时无法向老师开放！请在2026年中考后重试。\n" +
        "(You don't have the permission to access the requested resource. " +
        "It is either read-protected or not readable by the server.)")
    return render_template("not_allow.html"), http_code


@app.route("/avoid_titles")
def get_title_html():
    return render_template("avoid_titles.html")


@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"}), 200


@app.route("/maintenance")
def get_maintenance():
    return render_template("maintenance.html")


@app.route("/author")
def get_author():
    return render_template("author.html")


@app.route("/api/admin/maintenance", methods=["POST"])
def update_maintenance():
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        if not "m" in data:
            return api_response("error", "缺少参数", http_code=400)

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
        print(f"服务器错误: {str(e)}")
        print(traceback.format_exc())
        log_mgr.error("sys", f"更新maintenance时发生错误：{e}", "127.0.0.1")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/a-login", methods=["POST"])
def admin_login():
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        client_ip = request.remote_addr

        if not "pwd" in data:
            return api_response("error", "缺少字段", http_code=403)

        is_valid = data["pwd"] in (Config.STANDARD_PASSWORD, Config.MASTER_PASSWORD)

        success, message = locker.check_and_record(client_ip, is_valid)

        if success:
            return api_response("success", message)
        else:
            if "锁定" in message:
                return api_response("error", message, http_code=429)
            else:
                return api_response("error", message, http_code=403)
    except Exception as e:
        print(f"服务器错误: {str(e)}")
        print(traceback.format_exc())
        log_mgr.error("sys", f"在处理管理员登录时发生错误：{e}", "127.0.0.1")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/search", methods=["POST"])
def search():
    """统一的文章搜索接口"""
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        if not "slug" in data or not "type" in data:
            return api_response("error", "缺少参数 (slug, type)", http_code=400)

        mgr = psg_mgr if data["type"] == "article" else students_mgr
        msg, code = mgr.get_article(data["slug"])
        status = "success" if code == 200 else "error"
        return api_response(status, "", msg, code)
    except Exception as e:
        log_mgr.error("sys", f"搜索文章时发生错误：{e}", "127.0.0.1")
        return api_response("error", f"发生错误：{e}", http_code=500)


@app.route("/psg/<slug>")
def get_psg(slug):
    """教师传记页面"""
    return render_article(slug, psg_mgr, False)


@app.route("/student/<slug>")
def get_students(slug):
    """学生传记页面（使用统一模板）"""
    return render_article(slug, students_mgr, True)


def render_article(slug: str, mgr, is_stu: bool):
    """统一渲染文章页面"""
    try:
        psg, code = mgr.get_article(slug)

        if code != 200 or not psg:
            abort(404, description="没有此文章")

        # 安全提取数据
        psg_id = psg[0] if psg and len(psg) > 0 else 0
        title = psg[1] if len(psg) > 1 and psg[1] else "无标题"
        content = psg[2] if len(psg) > 2 and psg[2] else "[文章还在编辑中]"
        author_name = psg[4] if len(psg) > 4 and psg[4] else "未知"

        # 处理内容
        if not isinstance(content, str):
            content = str(content) if content else "[内容格式错误]"
        content = content.replace("\n", "<br>")

        if psg[7] == "draft":
            content = "[文章还在审核中……]"
        elif psg[7] == "rejected":
            content = ("<strong>该稿件存在根本性的价值导向问题，不予通过。请深刻反思创作导向，重新审视表达边界。</strong>" +
                       "\n——翱三通史传记审核系统")

        article = {
            "id": int(psg_id) if psg_id else 0,
            "title": str(title),
            "content": content,
            "author": f"作者：{author_name}",
            "is_stu": is_stu,
            "slug": slug
        }

        # 如果是教师文章，添加 sayings 字段
        if not is_stu and len(psg) > 8:
            sayings = psg[8] if psg[8] else "暂未统计语录"
            sayings_list = sayings.split("\n")
            for idx, saying in enumerate(sayings_list[:]):
                if len(sayings_list) == 1:
                    break
                saying = f"{idx+1}. {saying}"
                sayings_list[idx] = saying
            article["sayings"] = "<br>".join(sayings_list)

        # 使用统一的 article.html 模板
        return render_template("article.html", article=article)
    except Exception as e:
        traceback.print_exc()
        log_mgr.error("sys", f"渲染html时发生错误：{e}", "127.0.0.1")
        abort(500, description="处理请求时出错")


@app.route("/userPolicy")
def get_policy():
    return render_template("userPolicy.html")


@app.route("/api/get-articles", methods=["POST"])
def get_articles_by_aid():
    """统一的获取作者文章接口"""
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        if not "author" in data or not "type" in data:
            return api_response("error", "缺少参数 (author, type)", http_code=400)

        mgr = psg_mgr if data["type"] == "article" else students_mgr
        articles, code = mgr.get_by_author(data["author"])

        if code != 200:
            return api_response("error", str(articles), http_code=code)
        return api_response("success", "", articles)
    except Exception as e:
        log_mgr.error("sys", f"获取文章时发生错误：{e}", "127.0.0.1")
        return api_response("error", f"发生错误：{e}", http_code=500)


@app.route("/api/comments/get", methods=["POST"])
def get_comments():
    """获取评论（支持 articles 和 students）"""
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        article_id = data.get("article_id")
        student_id = data.get("student_id")

        if not article_id and not student_id:
            return api_response("error", "必须提供 article_id 或 student_id", http_code=400)

        comments, code = comments_mgr.get_comments(article_id, student_id)
        if code != 200:
            return api_response("error", str(comments), http_code=code)

        # 对匿名评论进行处理
        comments_res = [list(c) for c in comments]
        for comment in comments_res:
            if comment[10]:
                comment[3] = None

        return api_response("success", "", comments_res)
    except Exception as e:
        log_mgr.error("sys", f"获取评论时发生错误：{e}", "127.0.0.1")
        return api_response("error", f"发生错误：{e}", http_code=500)


@app.route("/api/comments/add", methods=["POST"])
def insert_comments():
    """添加评论（支持 articles 和 students）"""
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        required_fields = ['user_id', 'content']
        for field in required_fields:
            if field not in data:
                return api_response("error", f"缺少参数: {field}", http_code=400)

        msg, code = comments_mgr.insert_comment(
            content=data['content'],
            user_id=data['user_id'],
            parent_id=data.get('parent_id'),
            article_id=data.get('article_id'),
            student_id=data.get('student_id'),
            anonymous=data.get('anonymous'),
        )

        if code != 200:
            return api_response("error", msg, http_code=code)
        return api_response("success", msg)
    except Exception as e:
        log_mgr.error("sys", f"插入评论时发生错误：{e}", "127.0.0.1")
        return api_response("error", f"发生错误：{e}", http_code=500)


@app.route("/api/upload", methods=["POST"])
def upload():
    """统一上传接口"""
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        required = ["user", "pwd", "request", "article", "isReview"]
        if not all(k in data for k in required):
            return api_response("error", "缺少参数", http_code=400)

        # 密码验证
        if data["pwd"] not in [Config.STANDARD_PASSWORD, Config.MASTER_PASSWORD]:
            return api_response("error", "密码错误！", http_code=401)

        article = data["article"]
        if not data["isReview"]:
            auto_status, reviews = psg_reviewer.check_psg(article)
            article["status"] = "draft"
        else:
            if article["status"] == "draft":
                article["status"] = "rejected"

        mgr = psg_mgr if data.get("type", "article") == "article" else students_mgr

        if data["request"] == "upload":
            msg, code = mgr.insert(**article)
        elif data["request"] == "change":
            msg, code = mgr.update(**article)
        else:
            return api_response("error", "没有此操作", http_code=400)

        status = "success" if code == 200 else "error"
        if data["isReview"]:
            return api_response(status, "操作成功")
        return api_response(status, msg + reviews + "已加入审核列表。", http_code=code)
    except Exception as e:
        log_mgr.error("sys", f"上传文章时发生错误：{e}", "127.0.0.1")
        return api_response("error", f"发生错误：{e}", http_code=500)


@app.route("/api/saveUser", methods=["POST"])
def update_user():
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        if "user_id" not in data or "pwd" not in data or not "settings" in data:
            return api_response("error", "缺少参数", http_code=400)

        user_mgr.update_user(data["user_id"], data["pwd"], data["settings"])
        return api_response("success")
    except Exception as e:
        log_mgr.error("sys", f"重置密码时发生错误：{e}", "127.0.0.1")
        return api_response("error", f"发生错误: {e}", http_code=500)


@app.route("/api/log", methods=["POST"])
def log():
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        if "user" not in data or "action" not in data:
            return api_response("error", "缺少参数", http_code=400)

        user = data["user"]
        action = data["action"]

        return log_mgr.info(user, action, request.remote_addr)
    except Exception as e:
        log_mgr.error("sys", f"写入日志时发生错误：{e}", "127.0.0.1")
        return api_response("error", f"发生错误: {e}", http_code=500)


@app.route("/issues")
def get_issue():
    return render_template("issue.html")


@app.route("/api/issues", methods=["POST"])
def receive_issue():
    # 兼容两种提交方式
    if request.is_json:
        # JSON 格式
        data = request.get_json()
        issue_content = data.get('issue') if data else None
        user = data.get('username')
    else:
        # form-data 或 x-www-form-urlencoded 格式
        issue_content = request.form.get('issue')
        user = request.form.get('username')

    if not issue_content:
        return api_response("error", "问题不能为空", http_code=400)

    # 处理问题
    print(f"收到问题: {issue_content}")
    log_mgr.error(user, issue_content, request.remote_addr)
    upload_error(user, issue_content)
    return api_response("success", "提交成功，我们会尽快解决！")

@app.route('/api/settings', methods=["POST"])
def get_settings():
    try:
        if not request.is_json:
            return api_response("error", "请求必须为 JSON", http_code=400)

        data = request.get_json()
        if not "userID" in data:
            return api_response("error", "缺少参数", http_code=400)

        user_id = data["userID"]
        settings = user_mgr.get_settings(user_id)
        return api_response("success", "", {"settings": settings})
    except Exception as e:
        log_mgr.error("sys", f"获取用户设置时发生错误：{e}", "127.0.0.1")
        traceback.print_exc()
        return api_response("error", f"发生错误: {e}", http_code=500)

@app.route('/user')
def get_user():
    return render_template("user.html")

app.register_blueprint(face_bp, url_prefix="/face")
app.register_blueprint(admin_bp, url_prefix="/admin")


if __name__ == '__main__':
    app.run("0.0.0.0", 3, debug=True)
