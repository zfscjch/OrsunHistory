from flask import Blueprint, request, g, session
from .decorators import login_required
from .config import Config
from .get_titles import load_titles
from .error_handlers import check_user
from .psg_mgr import CommentsMgr
from .psg_reviewer import PsgReviewer
from .error_handlers import upload_error
from .api_response import api_response, request_not_json_res, request_miss_arg_res, server_error_res

api_bp = Blueprint("api", __name__)
comments_mgr = CommentsMgr()
psg_reviewer = PsgReviewer()

@api_bp.route("/login", methods=["POST"])
def login():
    """用户登录 - 支持滑动过期和记住我"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()

        if not "user" in data or not "pwd" in data:
            return request_miss_arg_res()

        user = data["user"]
        password = data["pwd"]
        remember_me = data.get("remember_me", False)  # ✅ 获取"记住我"选项
        user_mgr = g.user_mgr
        log_mgr = g.log_mgr
        user_id, is_active, msg = user_mgr.authenticate(user, password)

        if user_id:
            log_mgr.info(user, "登录成功", request.remote_addr)

            # ✅ 设置 Session（滑动过期）
            session.permanent = True  # 启用过期时间
            session['user_id'] = user_id
            session['user'] = user
            session['is_admin'] = user_mgr.is_admin(user_id)

            # ✅ 如果勾选"记住我"，生成长期令牌
            remember_token = None
            if remember_me:
                remember_token = user_mgr.generate_auto_login_token(user_id)

            status, select_msg, code = check_user(user)

            return api_response("success", msg, {
                "isActive": is_active,
                "error_hint": select_msg,
                "remember_token": remember_token  # ✅ 返回令牌
            })
        else:
            log_mgr.warn(user, "尝试登录账号失败", request.remote_addr)
            return api_response("error", msg)
    except Exception as e:
        return server_error_res("登录", e)


@api_bp.route("/auto-login", methods=["POST"])
def auto_login():
    """使用"记住我"令牌自动登录"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        token = data.get("token")

        if not token:
            return api_response("error", "缺少令牌", http_code=400)

        user_mgr = g.user_mgr
        user_id, username, is_admin = user_mgr.verify_auto_login_token(token)

        if user_id:
            # ✅ 重新建立 Session（滑动过期）
            session.permanent = True
            session['user_id'] = user_id
            session['user'] = username
            session['is_admin'] = is_admin

            log_mgr = g.log_mgr
            log_mgr.info(username, "自动登录成功", request.remote_addr)

            return api_response("success", "自动登录成功", {
                "user_id": user_id,
                "username": username
            })
        else:
            return api_response("error", "无效的自动登录令牌", http_code=401)

    except Exception as e:
        return server_error_res("自动登录", e)


@api_bp.route("/logout", methods=["POST"])
def logout():
    """退出登录 - 清除 Session 和记住我令牌"""
    try:
        user_mgr = g.user_mgr
        user_id = session.get('user_id')

        # ✅ 清除"记住我"令牌
        if user_id:
            user_mgr.clear_auto_login_token(user_id)

        # ✅ 清除 Session
        session.clear()

        return api_response("success", "已退出登录")
    except Exception as e:
        return server_error_res("退出登录", e)


@api_bp.route("/ping", methods=["POST"])
@login_required
def ping():
    """心跳接口 - 刷新 Session 过期时间（滑动过期）"""
    session.permanent = True  # ✅ 每次心跳都刷新过期时间
    return api_response("success", "pong")


@api_bp.route("/check-session", methods=["GET"])
def check_session():
    """检查 Session 是否有效"""
    if 'user_id' in session:
        session.permanent = True  # ✅ 检查时也刷新
        return api_response("success", "Session 有效", {
            "user_id": session['user_id'],
            "username": session['username']
        })
    return api_response("error", "Session 已过期", http_code=401)


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
    return api_response("error", "此端口已弃用", http_code=410)


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
@login_required
def get_articles_by_aid():
    """统一的获取作者文章接口"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not "type" in data:
            return request_miss_arg_res()

        psg_mgr = g.psg_mgr
        students_mgr = g.students_mgr
        mgr = psg_mgr if data["type"] == "article" else students_mgr
        pattern = ".*" if session['is_admin'] else session['user_id']
        articles, code = mgr.get_by_author(pattern)

        if code != 200:
            return api_response("error", str(articles), http_code=code)
        return api_response("success", "", articles)
    except Exception as e:
        return server_error_res("获取文章", e)


@api_bp.route("/comments/get", methods=["POST"])
@login_required
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
            if comment[10]:             # comment[10] 是 anonymous
                comment[3] = None       # comment[3] 是 user_id

        return api_response("success", "", comments_res)
    except Exception as e:
        return server_error_res("获取评论", e)


@api_bp.route("/comments/add", methods=["POST"])
@login_required
def insert_comments():
    """添加评论（支持 articles 和 students）"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if 'content' not in data:
            return request_miss_arg_res()

        user_id = session['user_id']
        msg, code = comments_mgr.insert_comment(
            content=data['content'],
            user_id=user_id,
            parent_id=data.get('parent_id'),
            article_id=data.get('article_id'),
            student_id=data.get('student_id'),
            anonymous=data.get('anonymous'),
            status=data.get('status')
        )

        if code != 200:
            return api_response("error", msg, http_code=code)
        return api_response("success", msg)
    except Exception as e:
        return server_error_res("添加评论", e)


@api_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    """统一上传接口"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        required = ["pwd", "request", "article", "isReview"]
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
        log_mgr.info(session['user'], f"修改文章:{article['title']}", request.remote_addr)

        status = "success" if code == 200 else "error"
        if data["isReview"] and not reviews:
            return api_response(status, "操作成功！")
        return api_response(status, msg + reviews + "已加入审核列表。", http_code=code)
    except Exception as e:
        return server_error_res("上传文章", e)


@api_bp.route("/saveUser", methods=["POST"])
@login_required
def update_user():
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if "user_id" not in data or "pwd" not in data or not "settings" in data:
            return request_miss_arg_res()

        user_mgr = g.user_mgr
        user_id = data['user_id']
        is_admin = session['is_admin']
        password = data['password']
        settings = data['settings']
        is_active = data.get("a", False)
        if user_id != session['user_id'] and not is_admin:
            return api_response("error", "权限不足，无法修改其他用户的信息", http_code=403)
        user_mgr.update_user(user_id, password, settings, is_active)
        return api_response("success")
    except Exception as e:
        return server_error_res("重置密码", e)


@api_bp.route("/log", methods=["POST"])
def log():
    return api_response("error", "此接口已弃用", http_code=410)


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


@api_bp.route('/settings', methods=["POST", "GET"])
@login_required
def get_settings():
    try:
        user_id = session['user_id']
        user_mgr = g.user_mgr
        settings = user_mgr.get_settings(user_id)
        return api_response("success", "", {"settings": settings})
    except Exception as e:
        return server_error_res("获取用户设置", e)


@api_bp.route('/get-id', methods=["POST"])
def get_user_id():
    return api_response("error", "此接口已弃用", http_code=410)

@api_bp.route('/currentUser', methods=["GET", "POST"])
@login_required
def get_current_user():
    try:
        current_user = {
            'user': session['user'],
            'user_id': session['user_id'],
            'is_admin': session['is_admin']
        }
        return api_response("success", data=current_user)
    except Exception as e:
        return server_error_res("获取当前用户", e)

@api_bp.route('/check', methods=["GET", "POST"])
@login_required
def check_user_msg():
    try:
        user_id = session["user_id"]
        res = comments_mgr.get_update_hint(user_id)

        return api_response("success", data={"users": res})
    except Exception as e:
        return server_error_res("初始检查用户", e)

@api_bp.route('/get-view', methods=["POST"])
@login_required
def get_articles_index():
    """统一的获取作者文章接口"""
    try:
        if not request.is_json:
            return request_not_json_res()

        data = request.get_json()
        if not "type" in data:
            return request_miss_arg_res()

        psg_mgr = g.psg_mgr
        students_mgr = g.students_mgr
        mgr = psg_mgr if data["type"] == "article" else students_mgr
        articles, code = mgr.get_by_author(".*")

        if code != 200:
            return api_response("error", str(articles), http_code=code)
        return api_response("success", "", articles)
    except Exception as e:
        return server_error_res("获取文章", e)

@api_bp.route('/logout')
@login_required
def clear_session():
    session.clear()
    return api_response("success", "已退出登录")
