# psg_mgr.py
from typing import Literal, Optional, Tuple, Union, List, Dict, Any
import mysql.connector
from .config import Config


class BaseArticleMgr:
    """文章管理基类，用于统一 articles 和 students 的操作"""

    def __init__(self, table_name: str):
        self.config = Config.MySQLConfig
        self.table_name = table_name

    def _get_connection(self):
        """获取数据库连接"""
        return mysql.connector.connect(**self.config)

    def get_article(self, slug: str) -> Tuple[Optional[tuple], int]:
        """根据 slug 获取单篇文章"""
        try:
            with self._get_connection() as cnx:
                with cnx.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE slug = %s", (slug,))
                    data = cursor.fetchone()
                    return data, 200
        except Exception as e:
            return e, 500

    def insert(self, title: str, content: str, slug: str, author: str,
               status: Literal["draft", "published"] = "draft", **kwargs) -> Tuple[str, int]:
        """插入文章"""
        try:
            # 处理 students 表没有 sayings 字段的情况
            if self.table_name == "students":
                with self._get_connection() as cnx:
                    with cnx.cursor() as cursor:
                        cursor.execute(
                            f"INSERT INTO {self.table_name} (title, content, slug, author, status) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (title, content, slug, author, status)
                        )
                        cnx.commit()
            else:
                # articles 表有 sayings 字段
                saying = kwargs.get('saying', '暂未统计语录')
                with self._get_connection() as cnx:
                    with cnx.cursor() as cursor:
                        cursor.execute(
                            f"INSERT INTO {self.table_name} (title, content, slug, author, sayings, status) "
                            "VALUES (%s, %s, %s, %s, %s, %s)",
                            (title, content, slug, author, saying, status)
                        )
                        cnx.commit()
            return "success", 200
        except Exception as e:
            return str(e), 500

    def update(self, title: str, content: str, slug: str, author: str,
               status: Literal["draft", "published"] = "draft", **kwargs) -> Tuple[str, int]:
        """更新或插入文章"""
        try:
            with self._get_connection() as cnx:
                with cnx.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE slug = %s", (slug,))
                    exists = cursor.fetchone()

                    if not exists:
                        return self.insert(title, content, slug, author, status, **kwargs)

                    if self.table_name == "students":
                        cursor.execute(
                            f"UPDATE {self.table_name} SET title = %s, content = %s, slug = %s, "
                            "author = %s, status = %s WHERE slug = %s",
                            (title, content, slug, author, status, slug)
                        )
                    else:
                        saying = kwargs.get('saying', '暂未统计语录')
                        cursor.execute(
                            f"UPDATE {self.table_name} SET title = %s, content = %s, slug = %s, "
                            "author = %s, status = %s, sayings = %s WHERE slug = %s",
                            (title, content, slug, author, status, saying, slug)
                        )
                    cnx.commit()
            return "success", 200
        except Exception as e:
            return str(e), 500

    def get_by_author(self, author: str) -> Tuple[Union[List, str], int]:
        """根据作者ID获取文章列表"""
        try:
            with self._get_connection() as cnx:
                with cnx.cursor() as cursor:
                    sql = f"SELECT title, slug FROM {self.table_name} WHERE author REGEXP %s"
                    cursor.execute(sql,(author,))
                    data = cursor.fetchall()
                    return data, 200
        except Exception as e:
            return str(e), 500

    def get_draft(self):
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT title, slug FROM {self.table_name} WHERE status = 'draft'")
                    data = cursor.fetchall()
                    return data, 200
        except Exception as e:
            return str(e), 500


class PsgMgr(BaseArticleMgr):
    """articles 表管理器"""

    def __init__(self):
        super().__init__("articles")

    def insert(self, title: str, content: str, slug: str, author: str,
               saying: str = "暂未统计语录",
               status: Literal["draft", "published"] = "draft") -> Tuple[str, int]:
        return super().insert(title, content, slug, author, status, saying=saying)

    def update(self, title: str, content: str, slug: str, author: str,
               saying: str = "暂未统计语录",
               status: Literal["draft", "published"] = "draft") -> Tuple[str, int]:
        return super().update(title, content, slug, author, status, saying=saying)


class StudentsMgr(BaseArticleMgr):
    """students 表管理器"""

    def __init__(self):
        super().__init__("students")


class CommentsMgr:
    """评论管理器，同时支持 articles 和 students"""

    def __init__(self):
        self.config = Config.MySQLConfig

    def _get_connection(self):
        return mysql.connector.connect(**self.config)

    def _check_target_exists(self, cursor, article_id: Optional[int], student_id: Optional[int]) -> bool:
        """检查目标文章是否存在"""
        if article_id:
            cursor.execute("SELECT id FROM articles WHERE id = %s", (article_id,))
            return cursor.fetchone() is not None
        elif student_id:
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            return cursor.fetchone() is not None
        return False

    def get_comments(self, article_id: Optional[int] = None, student_id: Optional[int] = None) -> Tuple[Union[List, str], int]:
        """获取评论列表"""
        try:
            with self._get_connection() as cnx:
                with cnx.cursor() as cursor:
                    if article_id:
                        cursor.execute(
                            "SELECT * FROM comments WHERE article_id = %s AND status = 'approved' ORDER BY created_at DESC",
                            (article_id,)
                        )
                    elif student_id:
                        cursor.execute(
                            "SELECT * FROM comments WHERE student_id = %s AND status = 'approved' ORDER BY created_at DESC",
                            (student_id,)
                        )
                    else:
                        return "缺少目标参数", 400
                    data = cursor.fetchall()
                    return data, 200
        except Exception as e:
            return str(e), 500

    def insert_comment(self, content: str, user_id: int, parent_id: Optional[int] = None,
                       article_id: Optional[int] = None, student_id: Optional[int] = None,
                       status: str = "approved", anonymous: bool = False) -> Tuple[str, int]:
        """添加评论"""
        try:
            if not article_id and not student_id:
                return "必须指定 article_id 或 student_id", 400

            with self._get_connection() as cnx:
                with cnx.cursor() as cursor:
                    # 检查目标是否存在
                    if not self._check_target_exists(cursor, article_id, student_id):
                        return "文章不存在", 400

                    # 检查父评论
                    if parent_id:
                        cursor.execute("SELECT id FROM comments WHERE id = %s", (parent_id,))
                        if not cursor.fetchone():
                            return "被回复的评论不存在", 400

                    cursor.execute(
                        """INSERT INTO comments (article_id, student_id, user_id, parent_id, content, status, anonymous)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (article_id, student_id, user_id, parent_id, content, status, anonymous)
                    )
                    cnx.commit()
            return "success", 200
        except Exception as e:
            return str(e), 500

    def update_comment(self, comment_id: int, content: str) -> Tuple[str, int]:
        """更新评论"""
        try:
            with self._get_connection() as cnx:
                with cnx.cursor() as cursor:
                    cursor.execute(
                        "UPDATE comments SET content = %s WHERE id = %s",
                        (content, comment_id)
                    )
                    cnx.commit()
            return "success", 200
        except Exception as e:
            return str(e), 500