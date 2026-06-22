import logging
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
        file_handler = logging.FileHandler(path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(remote_addr)s - %(user)s - %(message)s')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def info(self, user, action, remote_addr):
        try:
            # 使用LoggerAdapter自动添加user字段
            adapter = logging.LoggerAdapter(self.logger, {'user': user, "remote_addr": remote_addr})
            adapter.info(action)
            return api_response("success")
        except Exception as e:
            print(f"发生错误：{e}")
            return api_response("error", f"发生错误：{e}", http_code=500)

    def warn(self, user, action, remote_addr):
        try:
            # 使用LoggerAdapter自动添加user字段
            adapter = logging.LoggerAdapter(self.logger, {'user': user, "remote_addr": remote_addr})
            adapter.warning(action)
            return api_response("success")
        except Exception as e:
            print(f"发生错误：{e}")
            return api_response("error", f"发生错误：{e}", http_code=500)

    def error(self, user, action, remote_addr):
        try:
            # 使用LoggerAdapter自动添加user字段
            adapter = logging.LoggerAdapter(self.logger, {'user': user, "remote_addr": remote_addr})
            adapter.error(action)
            return api_response("success")
        except Exception as e:
            print(f"发生错误：{e}")
            return api_response("error", f"发生错误：{e}", http_code=500)

    def get_log(self):
        try:
            with open(self.path, "r", encoding="utf-8") as rf:
                data = rf.read()
            return data
        except Exception as e:
            print(f"发生错误：{e}")
            return f"发生错误：{e}"