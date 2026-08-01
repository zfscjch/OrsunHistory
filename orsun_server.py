import os
import re
import traceback
from flask import (
    Flask, request, jsonify, abort, render_template, redirect, g, url_for
)
from flask_cors import CORS
from functions import *

app = Flask(__name__)
CORS(app)

user_mgr = UserMgr()
psg_mgr = PsgMgr()
students_mgr = StudentsMgr()
os.chdir(os.path.dirname(__file__))
log_mgr = LogMgr("../logs/OrsunHistory/website.log")


@app.errorhandler(503)
def handle_503(error):
    return render_template("503.html"), 503


@app.before_request
def check():
    """检查访问浏览器和服务器是否符合要求"""
    g.user_mgr = user_mgr
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

@app.route("/outdatedLogin")
def outdated_login():
    return render_template("login_outdated.html")


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


@app.route("/not_allow")
def get_error_page():
    http_code = request.args.get("code", default=200, type=int)
    not_allow_ie = request.args.get("isIe", type=bool)
    if not not_allow_ie and http_code >= 400:
        abort(http_code)
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

@app.route("/psg/<slug>")
def get_psg(slug):
    """教师传记页面"""
    return render_article(slug, psg_mgr, False)


@app.route("/student/<slug>")
def get_students(slug):
    """学生传记页面（使用统一模板）"""
    return render_article(slug, students_mgr, True)


@app.route('/share')
def get_share():
    args = request.args
    slug = args.get("slug")
    article_type = args.get("t", "t")
    if article_type == "s":
        mgr = students_mgr
    else:
        mgr = psg_mgr
    return render_article(slug, mgr, article_type == "s", True)


def render_article(slug: str, mgr, is_stu: bool, share=False):
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
                       "<br>——翱三通史传记审核系统")

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

        # 使用分享文章的 share.html 模板
        if share:
            return render_template("share.html", article=article)

        # 使用统一的 article.html 模板
        return render_template("article.html", article=article)
    except Exception as e:
        traceback.print_exc()
        log_mgr.error("sys", f"渲染html时发生错误：{e}", "127.0.0.1")
        abort(500, description="处理请求时出错")


@app.route("/userPolicy")
def get_policy():
    return render_template("userPolicy.html")


@app.route("/issues")
def get_issue():
    return render_template("issue.html")


@app.route('/user')
def get_user():
    return render_template("user.html")

@app.route('/help')
def get_help():
    return render_template("help.html")

@app.route('/download/<slug>')
def get_download(slug):
    # 1. 严格验证 slug 格式（只允许小写字母）
    if not re.match(r'^[a-z]+$', slug):
        abort(400, description="无效的下载标识符")

    # 2. 将映射数据移到配置文件或数据库
    PSG_MAP = Config.PSG_MAP

    # 3. 安全的文件名映射
    doc_name = "翱三通史·"

    if slug == "hyq":
        doc_name += "主任本纪.docx"
    else:
        target = PSG_MAP.get(slug)
        if not target:
            abort(404, description="未找到对应的文档")
        # 4. 清理目标名称，移除危险字符
        safe_target = re.sub(r'[^\w\u4e00-\u9fff]', '', target)
        if not safe_target:
            abort(400, description="无效的文档名称")
        doc_name += safe_target + "传.docx"

    # 5. 使用安全的路径构建
    base_dir = app.root_path
    safe_path = os.path.join(base_dir, "static", "doc")
    full_path = os.path.join(safe_path, doc_name)

    # 6. 验证路径是否在允许的目录内（防止路径遍历）
    real_path = os.path.realpath(full_path)
    if not real_path.startswith(os.path.realpath(safe_path)):
        abort(403, description="禁止访问此路径")

    if not os.path.exists(real_path):
        abort(404, description="文件不存在")

    if not os.path.isfile(real_path):
        abort(400, description="无效的文件类型")

    # 7. 使用 url_for 生成安全的 URL
    return redirect(url_for('static', filename=f"doc/{doc_name}"))

@app.route('/version')
def get_version():
    with open('version/3.1.0beta.md', 'r', encoding='utf-8') as wf:
        data = wf.read()
    return render_template("version.html", data=data)

@app.route('/chat')
def get_chat():
    """翱三通史·聊天室 - 自动适配移动端"""
    user_agent = request.headers.get("User-Agent", "").lower()

    # 如果没有 User-Agent，默认返回桌面版（或根据实际情况处理）
    if not user_agent:
        return render_template("chat.html")

    # 移动设备检测正则（更完整）
    mobile_pattern = r"mobile|android|iphone|ipod|ipad|windows phone|ios|webos|blackberry|iemobile|opera mini"

    # 特殊检测：某些 iPad 的 UA 不包含 'ipad'，但包含 'mac os' 和 'safari'
    # 通过屏幕尺寸判断（但服务端无法获取，只能通过 UA 启发式）
    is_mobile = re.search(mobile_pattern, user_agent) is not None

    # 额外检测：Chrome 在移动设备上的 UA 包含 'mobile' 或 'android'
    if not is_mobile and "chrome" in user_agent:
        is_mobile = "mobile" in user_agent or "android" in user_agent

    # 检测微信内置浏览器
    if "micromessenger" in user_agent:
        is_mobile = True

    # 检测是否为平板（可选：某些 iPad 返回桌面版更好）
    if "ipad" in user_agent:
        # iPad 可以返回移动版或桌面版，根据需求决定
        # 这里默认返回移动版
        is_mobile = True

    if is_mobile:
        return render_template("mobileChat.html")

    return render_template("chat.html")

app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(face_bp, url_prefix="/face")
app.register_blueprint(admin_bp, url_prefix="/admin")


if __name__ == '__main__':
    app.run("0.0.0.0", 3, debug=True)
