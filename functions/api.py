from flask import Blueprint, request, g

from .config import Config
from .get_titles import load_titles
from .error_handlers import check_user
from .admin_locker import AccountLocker
from .psg_mgr import CommentsMgr
from .psg_reviewer import PsgReviewer
from .error_handlers import upload_error
from .api_response import api_response, request_not_json_res, request_miss_arg_res, server_error_res

api_bp = Blueprint("api", __name__)
comments_mgr = CommentsMgr()
psg_reviewer = PsgReviewer()
locker = AccountLocker("functions/db/login_locks.json")

@api_bp.route("/login", methods=["POST"])
def login():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()

        if not "user" in data or not "pwd" in data:
            return request_miss_arg_res()

        user = data["user"]
        password = data["pwd"]
        user_mgr = g.user_mgr
        log_mgr = g.log_mgr
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
    except Exception as e:
        return server_error_res("登录", e)


@api_bp.route("/titles")
def get_question():
    try:
        msg, code = load_titles("functions/db/titles.json")
        status = "success" if code == 200 else "error"
        return api_response(status, msg, http_code=code)
    except Exception as e:
        return server_error_res("获取防泄漏验证题目", e)


@api_bp.route("/a-login", methods=["POST"])
def admin_login():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        client_ip = request.remote_addr

        if not "pwd" in data:
            return request_miss_arg_res()

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
        return server_error_res("处理管理员登录", e)


@api_bp.route("/search", methods=["POST"])
def search():
    """统一的文章搜索接口"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not "slug" in data or not "type" in data:
            return request_miss_arg_res()

        psg_mgr = g.psg_mgr
        students_mgr = g.students_mgr
        mgr = psg_mgr if data["type"] == "article" else students_mgr
        msg, code = mgr.get_article(data["slug"])
        status = "success" if code == 200 else "error"
        return api_response(status, "", msg, code)
    except Exception as e:
        return server_error_res("搜索文章", e)


@api_bp.route("/get-articles", methods=["POST"])
def get_articles_by_aid():
    """统一的获取作者文章接口"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not "author" in data or not "type" in data:
            return request_miss_arg_res()

        psg_mgr = g.psg_mgr
        students_mgr = g.students_mgr
        mgr = psg_mgr if data["type"] == "article" else students_mgr
        articles, code = mgr.get_by_author(data["author"])

        if code != 200:
            return api_response("error", str(articles), http_code=code)
        return api_response("success", "", articles)
    except Exception as e:
        return server_error_res("获取文章", e)


@api_bp.route("/comments/get", methods=["POST"])
def get_comments():
    """获取评论（支持 articles 和 students）"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        article_id = data.get("article_id")
        student_id = data.get("student_id")

        if not article_id and not student_id:
            return request_miss_arg_res()

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
        return server_error_res("获取评论", e)


@api_bp.route("/comments/add", methods=["POST"])
def insert_comments():
    """添加评论（支持 articles 和 students）"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        required_fields = ['user_id', 'content']
        for field in required_fields:
            if field not in data:
                return request_miss_arg_res()

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
        return server_error_res("添加评论", e)


@api_bp.route("/upload", methods=["POST"])
def upload():
    """统一上传接口"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        required = ["user", "pwd", "request", "article", "isReview"]
        if not all(k in data for k in required):
            return request_miss_arg_res()

        # 密码验证
        if data["pwd"] not in [Config.STANDARD_PASSWORD, Config.MASTER_PASSWORD]:
            return api_response("error", "密码错误！", http_code=401)

        article = data["article"]
        reviews = ""
        if not data["isReview"] and data.get("type", "article") == "student":
            auto_status, reviews = psg_reviewer.check_psg(article)
            article["status"] = "draft"
        else:
            if article["status"] == "draft":
                article["status"] = "rejected"

        psg_mgr = g.psg_mgr
        students_mgr = g.students_mgr
        mgr = psg_mgr if data.get("type", "article") == "article" else students_mgr

        if data["request"] == "upload":
            msg, code = mgr.insert(**article)
        elif data["request"] == "change":
            msg, code = mgr.update(**article)
        else:
            return api_response("error", "没有此操作！", http_code=400)

        log_mgr = g.log_mgr
        log_mgr.info(data["user"], f"修改文章:{article['title']}", request.remote_addr)

        status = "success" if code == 200 else "error"
        if data["isReview"] or not 'reviews' in locals():
            return api_response(status, "操作成功！")
        return api_response(status, msg + reviews + "已加入审核列表。", http_code=code)
    except Exception as e:
        return server_error_res("上传文章", e)


@api_bp.route("/saveUser", methods=["POST"])
def update_user():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if "user_id" not in data or "pwd" not in data or not "settings" in data:
            return request_miss_arg_res()

        user_mgr = g.user_mgr
        user_mgr.update_user(data["user_id"], data["pwd"], data["settings"], data.get("a", False))
        return api_response("success")
    except Exception as e:
        return server_error_res("重置密码", e)


@api_bp.route("/log", methods=["POST"])
def log():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if "user" not in data or "action" not in data:
            return request_miss_arg_res()

        user = data["user"]
        action = data["action"]

        log_mgr = g.log_mgr
        return log_mgr.info(user, action, request.remote_addr)
    except Exception as e:
        return server_error_res("提交日志", e)


@api_bp.route("/issues", methods=["POST"])
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
    log_mgr = g.log_mgr
    log_mgr.error(user, issue_content, request.remote_addr)
    upload_error(user, issue_content)
    return api_response("success", "提交成功，我们会尽快解决！")


@api_bp.route('/settings', methods=["POST"])
def get_settings():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not "userID" in data:
            return request_miss_arg_res()

        user_id = data["userID"]
        user_mgr = g.user_mgr
        settings = user_mgr.get_settings(user_id)
        return api_response("success", "", {"settings": settings})
    except Exception as e:
        return server_error_res("获取用户设置", e)


@api_bp.route('/get-id', methods=["POST"])
def get_user_id():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not "user" in data:
            return request_miss_arg_res()

        user_id = data["user"]
        user_mgr = g.user_mgr
        uid = user_mgr.get_id(user_id)
        return api_response("success", "", {"id": uid})
    except Exception as e:
        return server_error_res("获取用户ID", e)