import re
import mysql.connector
from .config import Config

class PsgReviewer:
    def __init__(self):
        self.use_strict = True
        self.settings = {
            "author_real_name": True,
            "check_passage": True
        }

    def check_psg(self, psg: dict):
        if not self.use_strict:
            psg["status"] = "published"
            return True, "文章不存在问题！"

        if self.settings["author_real_name"]:
            is_real_name = self._check_user(psg["author"])
            if not is_real_name:
                return False, "作者必须实名！"

        if self.settings["check_passage"]:
            is_allow, text = self._check_content(psg["title"], psg["content"])
            if text:
                return False, text

        return True, "文章不存在问题！"

    def _check_user(self, author):
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE username = %s",
                               (author,))
                if cursor.fetchone():
                    return True
                return False

    def _check_content(self, title, content):
        target_name = title[:-1]
        with mysql.connector.connect(**Config.MySQLConfig) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE username = %s",
                               (target_name,))
                if cursor.fetchone():
                    pattern = re.compile("(" + target_name[0] + ")" + target_name[1:])
                    if re.match(pattern, content):
                        return True, ""
                    return False, "文章内容存在问题！"
                return False, "传记名称提取失败！"
