import json
import os
from datetime import datetime, timedelta

class AccountLocker:
    def __init__(self, path="db/login_locks.json"):
        self.lock_file = path
        self.max_attempts = 3
        self.lock_hours = 1

    def _load_data(self):
        if os.path.exists(self.lock_file):
            with open(self.lock_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_data(self, data):
        os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
        with open(self.lock_file, 'w') as f:
            json.dump(data, f, default=str)

    def check_and_record(self, ip, success):
        """检查并记录登录尝试"""
        data = self._load_data()

        if ip not in data:
            data[ip] = {"attempts": 0, "locked_until": None, "last_attempt": None}

        record = data[ip]

        # 检查是否在锁定期内
        if record["locked_until"]:
            locked_until = datetime.fromisoformat(record["locked_until"])
            if datetime.now() < locked_until:
                remaining = locked_until - datetime.now()
                return False, f"账号已锁定，{int(remaining.total_seconds()//60)}分{int(remaining.total_seconds()%60)}秒后重试"
            else:
                # 锁定已过期，重置
                record["attempts"] = 0
                record["locked_until"] = None

        if success:
            # 登录成功，重置
            record["attempts"] = 0
            record["locked_until"] = None
            self._save_data(data)
            return True, "登录成功"
        else:
            # 登录失败
            record["attempts"] += 1
            record["last_attempt"] = datetime.now().isoformat()

            if record["attempts"] >= self.max_attempts:
                # 锁定账户
                record["locked_until"] = (datetime.now() + timedelta(hours=self.lock_hours)).isoformat()
                self._save_data(data)
                return False, "密码错误次数过多，账号已锁定1小时"
            else:
                remaining = self.max_attempts - record["attempts"]
                self._save_data(data)
                return False, f"密码错误，还剩 {remaining} 次尝试"
                