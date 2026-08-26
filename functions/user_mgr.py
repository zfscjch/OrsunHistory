import json
import hashlib
import secrets
from datetime import datetime, timedelta
import bcrypt
import mysql.connector
from .config import Config

class UserMgr:
    def __init__(self):
        self.config = Config.MySQLConfig

    def register_user(self, username, password):
        """注册新用户"""
        # 生成密码哈希
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')  # 存储为字符串

        with mysql.connector.connect(**self.config) as cnx:
            with cnx.cursor() as cursor:
                try:
                    cursor.execute("""
                                   INSERT INTO users (username, password_hash, is_active)
                                   VALUES (%s, %s, %s)
                                   """, (username, password_hash, 1))
                    cnx.commit()
                    return cursor.lastrowid
                except mysql.connector.errors.IntegrityError as e:
                    if "UNIQUE constraint failed: users.username" in str(e):
                        return "用户已注册"
                raise

    def authenticate(self, username, password):
        """用户认证"""
        with mysql.connector.connect(**self.config) as cnx:
            with cnx.cursor() as cursor:
                cursor.execute("""
                               SELECT id, password_hash, login_attempts, account_locked, is_active
                               FROM users
                               WHERE username = %s
                               """, (username,))

                result = cursor.fetchone()
                if not result:
                    return None, 0, "用户不存在"

                user_id, stored_hash, attempts, locked, is_active = result

                # 检查账户是否锁定
                if locked:
                    return None, 0, "账户已被锁定"

                # 验证密码
                try:
                    is_correct = bcrypt.checkpw(
                        password.encode('utf-8'),
                        stored_hash.encode('utf-8')
                    )
                except ValueError:
                    return None, 0, "密码格式错误"

                if is_correct:
                    # 重置登录尝试次数
                    cursor.execute("""
                               UPDATE users
                               SET login_attempts = 0
                               WHERE id = %s
                               """, (user_id,))
                    cnx.commit()
                    return user_id, is_active, "登录成功"
                else:
                    # 增加失败次数
                    attempts += 1
                    if attempts >= 3:
                        cursor.execute("""
                                   UPDATE users
                                   SET account_locked = 1, login_attempts = %s
                                   WHERE id = %s
                                   """, (attempts, user_id))
                        cnx.commit()
                        return None, 0, "密码错误，账户已被锁定"
                    else:
                        cursor.execute("""
                                   UPDATE users
                                   SET login_attempts = %s
                                   WHERE id = %s
                                   """, (attempts, user_id))
                        cnx.commit()
                        return None, 0, f"密码错误，还剩 {5-attempts} 次尝试"

    def update_user(self, user_id, password="default", settings="default", change_active=False):
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        if type(settings).__name__ != 'str':
            settings = json.dumps(settings)

        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                if settings == "default":
                    sql = "UPDATE users SET password_hash = %s WHERE id = %s"
                    args = (password_hash, user_id)
                elif password == "default":
                    sql = "UPDATE users SET settings = %s WHERE id = %s"
                    args = (settings, user_id)
                else:
                    sql = "UPDATE users SET password_hash = %s, settings = %s WHERE id = %s"
                    args = (password_hash, settings, user_id)
                cursor.execute(sql, args)
                if change_active:
                    cursor.execute("UPDATE users SET is_active = 1 WHERE id = %s", (user_id,))
                conn.commit()

    def get_settings(self, user_id):
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                sql = "SELECT settings FROM users WHERE id = %s"
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                if not result:
                    return {}
                data = json.loads(str(result[0]))
                return data

    def generate_auto_login_token(self, user_id):
        """生成"记住我"令牌"""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now() + timedelta(days=30)

        with mysql.connector.connect(**self.config) as cnx:
            with cnx.cursor() as cursor:
                # 清除旧令牌
                cursor.execute(
                    "DELETE FROM auto_login_tokens WHERE user_id = %s",
                    (user_id,)
                )
                # 插入新令牌
                cursor.execute(
                    """INSERT INTO auto_login_tokens
                           (user_id, token_hash, expires_at, created_at)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, token_hash, expires_at, datetime.now())
                )
                cnx.commit()

        return raw_token

    def verify_auto_login_token(self, token):
        """验证"记住我"令牌"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        with mysql.connector.connect(**self.config) as cnx:
            with cnx.cursor() as cursor:
                cursor.execute(
                    """SELECT user_id, expires_at FROM auto_login_tokens
                       WHERE token_hash = %s""",
                    (token_hash,)
                )
                result = cursor.fetchone()

                if not result:
                    return None, None, False

                user_id, expires_at = result

                if expires_at < datetime.now():
                    cursor.execute(
                        "DELETE FROM auto_login_tokens WHERE token_hash = %s",
                        (token_hash,)
                    )
                    cnx.commit()
                    return None, None, False

                cursor.execute(
                    "SELECT username, is_admin FROM users WHERE id = %s",
                    (user_id,)
                )
                user_info = cursor.fetchone()
                if not user_info:
                    return None, None, False

                username, is_admin = user_info
                return user_id, username, bool(is_admin)

    def clear_auto_login_token(self, user_id):
        """清除用户的"记住我"令牌"""
        with mysql.connector.connect(**self.config) as cnx:
            with cnx.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM auto_login_tokens WHERE user_id = %s",
                    (user_id,)
                )
                cnx.commit()

    @staticmethod
    def is_admin(user_id):
        user_id = str(user_id)
        if not user_id or user_id == "None":
            return False
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
                is_admin = cursor.fetchone()
                return is_admin


