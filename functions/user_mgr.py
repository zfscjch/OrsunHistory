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
                    if attempts >= 5:
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

    def reset_password(self, user_id, password):
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                               (password_hash, user_id))
                conn.commit()



