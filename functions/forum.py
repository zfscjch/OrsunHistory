import mysql.connector
from mysql.connector import Error
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from .config import Config

forum_bp = Blueprint('forum', __name__, url_prefix='/forum')


class ForumDB:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def get_connection(self):
        if not self.connection or not self.connection.is_connected():
            try:
                self.connection = mysql.connector.connect(**Config.MySQLConfig)
                self.cursor = self.connection.cursor(dictionary=True)
            except Error as e:
                print(f"数据库连接失败: {e}")
                raise
        return self.connection

    def get_cursor(self):
        if not self.cursor:
            self.get_connection()
        return self.cursor

    def close_connection(self):
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.connection and self.connection.is_connected():
                self.connection.close()
                self.connection = None
        except Error as e:
            print(f"关闭连接失败: {e}")

    def execute_query(self, sql, params=None):
        cursor = self.get_cursor()
        try:
            cursor.execute(sql, params or ())
            return cursor
        except Error as e:
            print(f"查询执行失败: {e}")
            raise

    def execute_insert(self, sql, params=None):
        cursor = self.get_cursor()
        try:
            cursor.execute(sql, params or ())
            self.connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"插入失败: {e}")
            self.connection.rollback()
            raise

    def execute_update(self, sql, params=None):
        cursor = self.get_cursor()
        try:
            cursor.execute(sql, params or ())
            self.connection.commit()
            return cursor.rowcount
        except Error as e:
            print(f"更新失败: {e}")
            self.connection.rollback()
            raise

    def get_boards(self):
        """获取所有板块（包含是否为表白墙的标识）"""
        try:
            sql = """
                  SELECT id, name, description, icon, sort_order,
                         (name LIKE '%表白墙%') as is_anonymous_board
                  FROM forum_boards
                  WHERE is_active = TRUE
                  ORDER BY sort_order, id \
                  """
            cursor = self.execute_query(sql)
            return cursor.fetchall()
        except Error:
            return []

    def get_board_by_id(self, board_id):
        try:
            sql = "SELECT * FROM forum_boards WHERE id = %s AND is_active = TRUE"
            cursor = self.execute_query(sql, (board_id,))
            return cursor.fetchone()
        except Error:
            return None

    def get_threads_by_board(self, board_id, page=1, per_page=20):
        """获取板块帖子列表（处理匿名显示）"""
        offset = (page - 1) * per_page
        try:
            sql = """
                  SELECT t.*, u.username as author_name
                  FROM forum_threads t
                           LEFT JOIN users u ON t.author_id = u.id
                  WHERE t.board_id = %s AND t.is_deleted = FALSE
                  ORDER BY t.is_pinned DESC, t.last_reply_at DESC, t.created_at DESC
                  LIMIT %s OFFSET %s \
                  """
            cursor = self.execute_query(sql, (board_id, per_page, offset))
            threads = cursor.fetchall()

            for thread in threads:
                count_sql = "SELECT COUNT(*) as count FROM forum_replies WHERE thread_id = %s AND is_deleted = FALSE"
                count_cursor = self.execute_query(count_sql, (thread['id'],))
                thread['reply_count'] = count_cursor.fetchone()['count']

                # 如果是匿名帖子，替换作者名
                if thread.get('is_anonymous', False):
                    thread['author_name'] = '👤 匿名用户'

            count_sql = "SELECT COUNT(*) as total FROM forum_threads WHERE board_id = %s AND is_deleted = FALSE"
            count_cursor = self.execute_query(count_sql, (board_id,))
            total = count_cursor.fetchone()['total']

            return {
                'threads': threads,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page if total > 0 else 0
            }
        except Error:
            return {'threads': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0}

    def get_thread_by_id(self, thread_id):
        """获取帖子详情（处理匿名显示）"""
        try:
            sql = """
                  SELECT t.*, u.username as author_name
                  FROM forum_threads t
                           LEFT JOIN users u ON t.author_id = u.id
                  WHERE t.id = %s AND t.is_deleted = FALSE \
                  """
            cursor = self.execute_query(sql, (thread_id,))
            thread = cursor.fetchone()

            if thread:
                count_sql = "SELECT COUNT(*) as count FROM forum_replies WHERE thread_id = %s AND is_deleted = FALSE"
                count_cursor = self.execute_query(count_sql, (thread_id,))
                thread['reply_count'] = count_cursor.fetchone()['count']

                # 如果是匿名帖子，替换作者名
                if thread.get('is_anonymous', False):
                    thread['author_name'] = '👤 匿名用户'

            return thread
        except Error:
            return None

    def get_replies_by_thread(self, thread_id, page=1, per_page=20):
        """获取回复列表（处理匿名显示）"""
        offset = (page - 1) * per_page
        try:
            sql = """
                  SELECT r.*, u.username as author_name
                  FROM forum_replies r
                           LEFT JOIN users u ON r.author_id = u.id
                  WHERE r.thread_id = %s AND r.is_deleted = FALSE
                  ORDER BY r.created_at ASC
                  LIMIT %s OFFSET %s \
                  """
            cursor = self.execute_query(sql, (thread_id, per_page, offset))
            replies = cursor.fetchall()

            for reply in replies:
                like_sql = "SELECT COUNT(*) as count FROM forum_likes WHERE reply_id = %s"
                like_cursor = self.execute_query(like_sql, (reply['id'],))
                reply['like_count'] = like_cursor.fetchone()['count']

                # 如果是匿名回复，替换作者名
                if reply.get('is_anonymous', False):
                    reply['author_name'] = '👤 匿名用户'

            count_sql = "SELECT COUNT(*) as total FROM forum_replies WHERE thread_id = %s AND is_deleted = FALSE"
            count_cursor = self.execute_query(count_sql, (thread_id,))
            total = count_cursor.fetchone()['total']

            return {
                'replies': replies,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page if total > 0 else 0
            }
        except Error:
            return {'replies': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0}

    def create_thread(self, board_id, title, content, author_id, is_anonymous=False):
        """创建帖子（支持匿名）"""
        try:
            sql = """
                  INSERT INTO forum_threads
                  (board_id, title, content, author_id, is_anonymous, last_reply_at, created_at, updated_at)
                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
                  """
            now = datetime.now()
            params = (board_id, title, content, author_id, is_anonymous, now, now, now)
            return self.execute_insert(sql, params)
        except Error:
            return None

    def create_reply(self, thread_id, content, author_id, is_anonymous=False):
        """创建回复（支持匿名）"""
        try:
            sql = """
                  INSERT INTO forum_replies (thread_id, content, author_id, is_anonymous, created_at, updated_at)
                  VALUES (%s, %s, %s, %s, %s, %s) \
                  """
            now = datetime.now()
            params = (thread_id, content, author_id, is_anonymous, now, now)
            reply_id = self.execute_insert(sql, params)

            update_sql = """
                         UPDATE forum_threads
                         SET reply_count = reply_count + 1,
                             last_reply_id = %s,
                             last_reply_at = %s,
                             updated_at = %s
                         WHERE id = %s \
                         """
            update_params = (reply_id, now, now, thread_id)
            self.execute_update(update_sql, update_params)

            return reply_id
        except Error:
            return None

    def is_anonymous_board(self, board_id):
        """检查板块是否为匿名板块（表白墙）"""
        try:
            sql = "SELECT name FROM forum_boards WHERE id = %s AND is_active = TRUE"
            cursor = self.execute_query(sql, (board_id,))
            result = cursor.fetchone()
            if result and '表白墙' in result['name']:
                return True
            return False
        except Error:
            return False

    def get_author_id_by_thread(self, thread_id):
        try:
            sql = "SELECT author_id FROM forum_threads WHERE id = %s AND is_deleted = FALSE"
            cursor = self.execute_query(sql, (thread_id,))
            result = cursor.fetchone()
            return result['author_id'] if result else None
        except Error:
            return None

    def update_thread_view(self, thread_id):
        try:
            sql = "UPDATE forum_threads SET view_count = view_count + 1 WHERE id = %s"
            return self.execute_update(sql, (thread_id,))
        except Error:
            return False

    def toggle_pin_thread(self, thread_id, is_pinned):
        try:
            sql = "UPDATE forum_threads SET is_pinned = %s, updated_at = %s WHERE id = %s"
            params = (is_pinned, datetime.now(), thread_id)
            return self.execute_update(sql, params)
        except Error:
            return False

    def toggle_lock_thread(self, thread_id, is_locked):
        try:
            sql = "UPDATE forum_threads SET is_locked = %s, updated_at = %s WHERE id = %s"
            params = (is_locked, datetime.now(), thread_id)
            return self.execute_update(sql, params)
        except Error:
            return False

    def delete_thread(self, thread_id):
        try:
            sql = "UPDATE forum_threads SET is_deleted = TRUE, updated_at = %s WHERE id = %s"
            params = (datetime.now(), thread_id)
            return self.execute_update(sql, params)
        except Error:
            return False

    def toggle_like(self, user_id, reply_id=None, thread_id=None):
        try:
            if reply_id:
                check_sql = "SELECT id FROM forum_likes WHERE user_id = %s AND reply_id = %s"
                params = (user_id, reply_id)
            else:
                check_sql = "SELECT id FROM forum_likes WHERE user_id = %s AND thread_id = %s"
                params = (user_id, thread_id)

            cursor = self.execute_query(check_sql, params)
            existing = cursor.fetchone()

            if existing:
                delete_sql = "DELETE FROM forum_likes WHERE id = %s"
                self.execute_update(delete_sql, (existing['id'],))
                liked = False
            else:
                if reply_id:
                    insert_sql = "INSERT INTO forum_likes (user_id, reply_id) VALUES (%s, %s)"
                    params = (user_id, reply_id)
                else:
                    insert_sql = "INSERT INTO forum_likes (user_id, thread_id) VALUES (%s, %s)"
                    params = (user_id, thread_id)
                self.execute_insert(insert_sql, params)
                liked = True

            return liked
        except Error:
            return False

    def get_user_likes(self, user_id):
        try:
            sql = "SELECT reply_id, thread_id FROM forum_likes WHERE user_id = %s"
            cursor = self.execute_query(sql, (user_id,))
            likes = cursor.fetchall()
            return {
                'reply_ids': [l['reply_id'] for l in likes if l['reply_id']],
                'thread_ids': [l['thread_id'] for l in likes if l['thread_id']]
            }
        except Error:
            return {'reply_ids': [], 'thread_ids': []}

    def search_threads(self, keyword, page=1, per_page=20):
        offset = (page - 1) * per_page
        try:
            sql = """
                  SELECT t.*, u.username as author_name, b.name as board_name
                  FROM forum_threads t
                           LEFT JOIN users u ON t.author_id = u.id
                           LEFT JOIN forum_boards b ON t.board_id = b.id
                  WHERE t.is_deleted = FALSE
                    AND (t.title LIKE %s OR t.content LIKE %s)
                  ORDER BY t.created_at DESC
                  LIMIT %s OFFSET %s \
                  """
            search_pattern = f'%{keyword}%'
            params = (search_pattern, search_pattern, per_page, offset)
            cursor = self.execute_query(sql, params)
            threads = cursor.fetchall()

            count_sql = """
                        SELECT COUNT(*) as total
                        FROM forum_threads
                        WHERE is_deleted = FALSE
                          AND (title LIKE %s OR content LIKE %s) \
                        """
            count_params = (search_pattern, search_pattern)
            count_cursor = self.execute_query(count_sql, count_params)
            total = count_cursor.fetchone()['total']

            return {
                'threads': threads,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page if total > 0 else 0
            }
        except Error:
            return {'threads': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0}

    def get_forum_stats(self):
        try:
            stats = {}
            cursor = self.execute_query("SELECT COUNT(*) as total FROM forum_threads WHERE is_deleted = FALSE")
            stats['total_threads'] = cursor.fetchone()['total']

            cursor = self.execute_query("SELECT COUNT(*) as total FROM forum_replies WHERE is_deleted = FALSE")
            stats['total_replies'] = cursor.fetchone()['total']

            cursor = self.execute_query("SELECT COUNT(*) as total FROM users")
            stats['total_users'] = cursor.fetchone()['total']

            today = datetime.now().strftime('%Y-%m-%d')
            cursor = self.execute_query(
                "SELECT COUNT(*) as total FROM forum_threads WHERE DATE(created_at) = %s AND is_deleted = FALSE",
                (today,)
            )
            stats['today_threads'] = cursor.fetchone()['total']

            return stats
        except Error:
            return {}

    def get_hot_threads(self, limit=10):
        try:
            sql = """
                  SELECT t.*, u.username as author_name,
                         (SELECT COUNT(*) FROM forum_replies WHERE thread_id = t.id) as reply_count
                  FROM forum_threads t
                           LEFT JOIN users u ON t.author_id = u.id
                  WHERE t.is_deleted = FALSE
                  ORDER BY (t.view_count + t.reply_count * 10) DESC
                  LIMIT %s \
                  """
            cursor = self.execute_query(sql, (limit,))
            return cursor.fetchall()
        except Error:
            return []

    def get_recent_threads(self, limit=10):
        try:
            sql = """
                  SELECT t.*, u.username as author_name
                  FROM forum_threads t
                           LEFT JOIN users u ON t.author_id = u.id
                  WHERE t.is_deleted = FALSE
                  ORDER BY t.created_at DESC
                  LIMIT %s \
                  """
            cursor = self.execute_query(sql, (limit,))
            return cursor.fetchall()
        except Error:
            return []


@forum_bp.route('/')
def index():
    db = ForumDB()
    try:
        boards = db.get_boards()
        stats = db.get_forum_stats()
        return render_template('forum_index.html', boards=boards, stats=stats)
    finally:
        db.close_connection()


@forum_bp.route('/board/<int:board_id>')
def board(board_id):
    page = request.args.get('page', 1, type=int)
    db = ForumDB()
    try:
        board_info = db.get_board_by_id(board_id)
        if not board_info:
            return render_template('forum_not_found.html'), 404

        thread_data = db.get_threads_by_board(board_id, page)
        return render_template('forum_board.html',
                               board=board_info,
                               threads=thread_data['threads'],
                               pagination=thread_data)
    finally:
        db.close_connection()


@forum_bp.route('/thread/<int:thread_id>')
def thread(thread_id):
    page = request.args.get('page', 1, type=int)
    db = ForumDB()
    try:
        thread_info = db.get_thread_by_id(thread_id)
        if not thread_info:
            return render_template('forum_not_found.html'), 404

        db.update_thread_view(thread_id)
        reply_data = db.get_replies_by_thread(thread_id, page)

        return render_template('forum_thread.html',
                               thread=thread_info,
                               replies=reply_data['replies'],
                               pagination=reply_data)
    finally:
        db.close_connection()


@forum_bp.route('/new_thread', methods=['GET', 'POST'])
def new_thread():
    db = ForumDB()
    try:
        if request.method == 'GET':
            boards = db.get_boards()
            return render_template('forum_new.html', boards=boards)

        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求格式错误'})

        user_id = data.get('user_id')
        board_id = data.get('board_id')
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        is_anonymous = data.get('is_anonymous', False)

        if not all([board_id, title, content]):
            return jsonify({'code': 400, 'message': '所有字段都是必填的'})

        if len(title) < 5:
            return jsonify({'code': 400, 'message': '标题至少需要5个字符'})

        if len(content) < 10:
            return jsonify({'code': 400, 'message': '内容至少需要10个字符'})

        # 非匿名发帖需要登录
        if not is_anonymous and not user_id:
            return jsonify({'code': 401, 'message': '请先登录'})

        thread_id = db.create_thread(board_id, title, content, user_id, is_anonymous)

        if thread_id:
            return jsonify({'code': 200, 'message': '帖子创建成功', 'data': {'thread_id': thread_id}})
        else:
            return jsonify({'code': 500, 'message': '创建帖子失败，请稍后重试'})
    finally:
        db.close_connection()


# 修改 reply 路由
@forum_bp.route('/reply/<int:thread_id>', methods=['POST'])
def create_reply(thread_id):
    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '请求格式错误'})

    user_id = data.get('user_id')
    content = data.get('content', '').strip()
    is_anonymous = data.get('is_anonymous', False)

    if not content:
        return jsonify({'code': 400, 'message': '回复内容不能为空'})

    if len(content) < 2:
        return jsonify({'code': 400, 'message': '回复内容至少需要2个字符'})

    db = ForumDB()
    try:
        thread_info = db.get_thread_by_id(thread_id)
        if not thread_info:
            return jsonify({'code': 404, 'message': '帖子不存在'})

        if thread_info['is_locked']:
            return jsonify({'code': 403, 'message': '该帖子已被锁定，无法回复'})

        # 非匿名回复需要登录
        if not is_anonymous and not user_id:
            return jsonify({'code': 401, 'message': '请先登录'})

        reply_id = db.create_reply(thread_id, content, user_id, is_anonymous)

        if reply_id:
            return jsonify({'code': 200, 'message': '回复成功', 'data': {'reply_id': reply_id}})
        else:
            return jsonify({'code': 500, 'message': '回复失败，请稍后重试'})
    finally:
        db.close_connection()


@forum_bp.route('/api/thread/<int:thread_id>/pin', methods=['POST'])
def pin_thread(thread_id):
    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '请求格式错误'})

    user_id = data.get('user_id')
    is_admin = data.get('is_admin', False)

    if not user_id:
        return jsonify({'code': 401, 'message': '请先登录'})

    if not is_admin:
        return jsonify({'code': 403, 'message': '需要管理员权限'})

    is_pinned = data.get('is_pinned', False)

    db = ForumDB()
    try:
        result = db.toggle_pin_thread(thread_id, is_pinned)
        if result:
            return jsonify({'code': 200, 'message': '操作成功'})
        else:
            return jsonify({'code': 500, 'message': '操作失败'})
    finally:
        db.close_connection()


@forum_bp.route('/api/thread/<int:thread_id>/lock', methods=['POST'])
def lock_thread(thread_id):
    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '请求格式错误'})

    user_id = data.get('user_id')
    is_admin = data.get('is_admin', False)

    if not user_id:
        return jsonify({'code': 401, 'message': '请先登录'})

    if not is_admin:
        return jsonify({'code': 403, 'message': '需要管理员权限'})

    is_locked = data.get('is_locked', False)

    db = ForumDB()
    try:
        result = db.toggle_lock_thread(thread_id, is_locked)
        if result:
            return jsonify({'code': 200, 'message': '操作成功'})
        else:
            return jsonify({'code': 500, 'message': '操作失败'})
    finally:
        db.close_connection()


@forum_bp.route('/api/thread/<int:thread_id>/delete', methods=['POST'])
def delete_thread(thread_id):
    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '请求格式错误'})

    user_id = data.get('user_id')
    is_admin = data.get('is_admin', False)

    if not user_id:
        return jsonify({'code': 401, 'message': '请先登录'})

    db = ForumDB()
    try:
        thread_info = db.get_thread_by_id(thread_id)
        if not thread_info:
            return jsonify({'code': 404, 'message': '帖子不存在'})

        # 检查权限：管理员或作者本人
        author_id = db.get_author_id_by_thread(thread_id)
        if not (is_admin or author_id == user_id):
            return jsonify({'code': 403, 'message': '无权限删除此帖子'})

        result = db.delete_thread(thread_id)
        if result:
            return jsonify({'code': 200, 'message': '删除成功'})
        else:
            return jsonify({'code': 500, 'message': '删除失败'})
    finally:
        db.close_connection()


@forum_bp.route('/api/like', methods=['POST'])
def toggle_like():
    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '请求格式错误'})

    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'code': 401, 'message': '请先登录'})

    reply_id = data.get('reply_id')
    thread_id = data.get('thread_id')

    if not (reply_id or thread_id):
        return jsonify({'code': 400, 'message': '请指定点赞对象'})

    db = ForumDB()
    try:
        liked = db.toggle_like(user_id, reply_id, thread_id)
        if liked is not False:
            return jsonify({'code': 200, 'message': '操作成功', 'data': {'liked': liked}})
        else:
            return jsonify({'code': 500, 'message': '操作失败'})
    finally:
        db.close_connection()


@forum_bp.route('/search')
def search():
    keyword = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)

    if not keyword:
        return redirect(url_for('forum.index'))

    db = ForumDB()
    try:
        results = db.search_threads(keyword, page)
        return render_template('forum_search.html',
                               keyword=keyword,
                               threads=results['threads'],
                               pagination=results)
    finally:
        db.close_connection()


@forum_bp.route('/stats')
def stats():
    db = ForumDB()
    try:
        stats = db.get_forum_stats()
        return jsonify({'code': 200, 'data': stats})
    finally:
        db.close_connection()


def init_forum_database():
    db = ForumDB()
    conn = db.get_connection()
    cursor = db.get_cursor()

    try:
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS forum_boards (
                                                                   id INT PRIMARY KEY AUTO_INCREMENT,
                                                                   name VARCHAR(100) NOT NULL,
                                                                   description TEXT,
                                                                   icon VARCHAR(50) DEFAULT '📄',
                                                                   sort_order INT DEFAULT 0,
                                                                   is_active BOOLEAN DEFAULT TRUE,
                                                                   created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                                                   updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                       )
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS forum_threads (
                                                                    id INT PRIMARY KEY AUTO_INCREMENT,
                                                                    board_id INT NOT NULL,
                                                                    title VARCHAR(200) NOT NULL,
                                                                    content TEXT NOT NULL,
                                                                    author_id INT NOT NULL,
                                                                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                                                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                                                    view_count INT DEFAULT 0,
                                                                    reply_count INT DEFAULT 0,
                                                                    last_reply_id INT,
                                                                    last_reply_at DATETIME,
                                                                    is_pinned BOOLEAN DEFAULT FALSE,
                                                                    is_locked BOOLEAN DEFAULT FALSE,
                                                                    is_deleted BOOLEAN DEFAULT FALSE,
                                                                    FOREIGN KEY (board_id) REFERENCES forum_boards(id)
                       )
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS forum_replies (
                                                                    id INT PRIMARY KEY AUTO_INCREMENT,
                                                                    thread_id INT NOT NULL,
                                                                    content TEXT NOT NULL,
                                                                    author_id INT NOT NULL,
                                                                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                                                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                                                    is_deleted BOOLEAN DEFAULT FALSE,
                                                                    FOREIGN KEY (thread_id) REFERENCES forum_threads(id)
                       )
                       """)

        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS forum_likes (
                                                                  id INT PRIMARY KEY AUTO_INCREMENT,
                                                                  reply_id INT,
                                                                  thread_id INT,
                                                                  user_id INT NOT NULL,
                                                                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                                                  FOREIGN KEY (reply_id) REFERENCES forum_replies(id),
                                                                  FOREIGN KEY (thread_id) REFERENCES forum_threads(id)
                       )
                       """)

        conn.commit()
        print("✅ 论坛数据库初始化成功！")
        return True

    except Error as e:
        print(f"❌ 数据库初始化失败: {e}")
        conn.rollback()
        return False
    finally:
        db.close_connection()


@forum_bp.context_processor
def inject_forum_context():
    return {}


if __name__ == '__main__':
    init_forum_database()