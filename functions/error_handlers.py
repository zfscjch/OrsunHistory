import mysql.connector
from .config import Config


def search_error(error_id):
    try:
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM issues WHERE id = %s", (error_id,))
                one_error = cursor.fetchone()
                return "success", one_error, 200
    except Exception as e:
        print(f"发生错误:{e}")
        return "error", f"发生错误:{e}", 500


def upload_error(user, error):
    try:
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO issues (upload_user, error) "
                               "VALUES (%s, %s)",
                               (user, error))
                conn.commit()
                return "success", "", 200
    except Exception as e:
        print(f"发生错误:{e}")
        return "error", f"发生错误:{e}", 500


def get_all():
    try:
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM issues WHERE is_resolve = FALSE")
                all_errors = cursor.fetchall()
                return "success", all_errors, 200
    except Exception as e:
        print(f"发生错误:{e}")
        return "error", f"发生错误:{e}", 500


def resolve_error(error_id):
    try:
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE issues SET is_resolve = TRUE "
                               "WHERE id = %s",
                               (error_id,))
                conn.commit()
                return "success", "", 200
    except Exception as e:
        print(f"发生错误:{e}")
        return "error", f"发生错误:{e}", 500


def check_user(user):
    try:
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM issues "
                               "WHERE is_resolve = TRUE AND is_broadcast = FALSE "
                               "AND upload_user = %s", (user,))
                error_ids = cursor.fetchall()
                print(error_ids)
                if error_ids:
                    issues_ids = []
                    for issue_id in error_ids:
                        cursor.execute("UPDATE issues SET is_broadcast = TRUE WHERE id = %s",
                                       (issue_id[0],))
                        conn.commit()
                        issues_ids.append(issue_id[0])
                    return "success", (f"您提交的错误(ID: {','.join(map(str, issues_ids))})已经修复，" +
                                       f"感谢您对翱三通史官网的信任！"), 200
                return "success", None, 200
    except Exception as e:
        print(f"发生错误:{e}")
        return "error", "", 500
