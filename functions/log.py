import logging
from logging.handlers import RotatingFileHandler
from flask import session, request, g
from .api_response import api_response

class LogMgr:
    def __init__(self, path):
        self.path = path

        # 配置logger
        self.logger = logging.getLogger('LogMgr')
        self.logger.setLevel(logging.INFO)

        # 清除可能存在的旧handler
        if self.logger.handlers:
            self.logger.handlers.clear()

        # 创建文件handler
        file_handler = RotatingFileHandler(
            path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(remote_addr)s - %(user)s - %(message)s')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def info(self, user, action, remote_addr="127.0.0.1"):
        try:
            # 使用LoggerAdapter自动添加user字段
            if user == "admin":
                return
            adapter = logging.LoggerAdapter(self.logger, {'user': user, "remote_addr": remote_addr})
            adapter.info(action)
        except Exception as e:
            print(f"发生错误：{e}")
            self.error("log_mgr", f"在保存info日志时发生错误：{e}")

    def warn(self, user, action, remote_addr="127.0.0.1"):
        try:
            # 使用LoggerAdapter自动添加user字段
            adapter = logging.LoggerAdapter(self.logger, {'user': user, "remote_addr": remote_addr})
            adapter.warning(action)
        except Exception as e:
            print(f"发生错误：{e}")
            self.error("log_mgr", f"在保存warn日志时发生错误：{e}")

    def error(self, user, action, remote_addr="system"):
        try:
            # 使用LoggerAdapter自动添加user字段
            adapter = logging.LoggerAdapter(self.logger, {'user': user, "remote_addr": remote_addr})
            adapter.error(action)
        except Exception as e:
            print(f"发生错误：{e}")

    def get_log(self):
        try:
            with open(self.path, "r", encoding="utf-8") as rf:
                data = rf.read()
            return data
        except Exception as e:
            print(f"发生错误：{e}")
            return f"发生错误：{e}"