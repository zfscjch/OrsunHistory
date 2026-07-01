import mysql.connector
from .config import Config

def get_user(username):
    with mysql.connector.connect(**Config.MySQLConfig) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT id FROM users
                           WHERE username = %s
                           """, (username,))
            user_id = cursor.fetchone()[0]
            if user_id:
                is_teacher = (49 <= user_id <= 60)
                return "success", {"user": username, "isT": is_teacher, "user_id": user_id}
            return "error", "没有此用户"