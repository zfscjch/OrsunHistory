import os
import json
import time
import hashlib
from datetime import datetime
from typing import Optional, Tuple, List
from .log import LogMgr


class BanMgr:
    """封禁管理器 - 纯文件存储 + 内存缓存"""
    
    # 封禁数据存储路径
    BAN_FILE = os.path.join(os.path.dirname(__file__), 'db', 'bans.json')
    # 请求计数存储路径（用于频率限制）
    RATE_FILE = os.path.join(os.path.dirname(__file__), 'db', 'rate_limits.json')
    
    def __init__(self, log_mgr=None):
        self.log = log_mgr or LogMgr("../logs/OrsunHistory/ban.log")
        self._temp_bans = {}  # 内存缓存：key -> (过期时间戳, 原因)
        self._loaded = False
        self._load_bans()
    
    def _load_bans(self):
        """从文件加载封禁数据到内存"""
        try:
            if os.path.exists(self.BAN_FILE):
                with open(self.BAN_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    now = time.time()
                    # 只加载未过期的封禁
                    for key, ban_info in data.items():
                        expire_at = ban_info.get('expire_at')
                        if expire_at is None or expire_at > now:
                            self._temp_bans[key] = (expire_at or float('inf'), ban_info['reason'])
            self._loaded = True
            if self.log:
                self.log.info("system", f"加载封禁数据成功，共 {len(self._temp_bans)} 条有效封禁")
        except Exception as e:
            self._temp_bans = {}
            if self.log:
                self.log.error("system", f"加载封禁数据失败: {e}")
    
    def _save_bans(self):
        """保存封禁数据到文件（只保存未过期的）"""
        try:
            now = time.time()
            data = {}
            for key, (expire_at, reason) in self._temp_bans.items():
                if expire_at is None or expire_at > now:
                    data[key] = {
                        'reason': reason,
                        'expire_at': expire_at if expire_at != float('inf') else None
                    }
            
            with open(self.BAN_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            if self.log:
                self.log.error("system", f"保存封禁数据失败: {e}")
            return False
    
    def _generate_key(self, target_type: str, target_value: str) -> str:
        """生成封禁记录的 key"""
        # 使用哈希确保 key 安全（防止特殊字符）
        value_hash = hashlib.md5(target_value.encode()).hexdigest()
        return f"{target_type}:{value_hash}"
    
    def check_banned(self, target_type: str, target_value: str) -> Tuple[bool, Optional[str]]:
        """检查是否被封禁，返回 (是否被封禁, 原因)"""
        if not target_value:
            return False, None
        
        key = self._generate_key(target_type, target_value)
        now = time.time()
        
        if key in self._temp_bans:
            expire_at, reason = self._temp_bans[key]
            if expire_at is None or expire_at > now:
                return True, reason
            else:
                # 过期了，移除缓存
                del self._temp_bans[key]
                # 自动保存更新后的状态
                self._save_bans()
                return False, None
        
        return False, None
    
    def ban_ip(self, ip: str, reason: str, duration_seconds: Optional[int] = None, 
               banned_by: str = "system") -> bool:
        """封禁 IP"""
        if not ip:
            return False
        
        key = self._generate_key("ip", ip)
        expire_at = None if duration_seconds is None else time.time() + duration_seconds
        self._temp_bans[key] = (expire_at if expire_at is not None else float('inf'), reason)
        
        saved = self._save_bans()
        
        # 构建日志信息
        duration_str = "永久" if duration_seconds is None else f"{duration_seconds}秒"
        if self.log:
            self.log.info(banned_by, f"封禁IP: {ip}, 原因: {reason}, 时长: {duration_str}")
        
        return saved
    
    def ban_user(self, user_id: str, reason: str, duration_seconds: Optional[int] = None,
                 banned_by: str = "system") -> bool:
        """封禁用户"""
        if not user_id:
            return False
        
        key = self._generate_key("user", user_id)
        expire_at = None if duration_seconds is None else time.time() + duration_seconds
        self._temp_bans[key] = (expire_at if expire_at is not None else float('inf'), reason)
        
        saved = self._save_bans()
        
        duration_str = "永久" if duration_seconds is None else f"{duration_seconds}秒"
        if self.log:
            self.log.info(banned_by, f"封禁用户: {user_id}, 原因: {reason}, 时长: {duration_str}")
        
        return saved
    
    def unban_ip(self, ip: str) -> bool:
        """解封 IP"""
        key = self._generate_key("ip", ip)
        if key in self._temp_bans:
            del self._temp_bans[key]
            if self.log:
                self.log.info("system", f"解封IP: {ip}")
            return self._save_bans()
        return True
    
    def unban_user(self, user_id: str) -> bool:
        """解封用户"""
        key = self._generate_key("user", user_id)
        if key in self._temp_bans:
            del self._temp_bans[key]
            if self.log:
                self.log.info("system", f"解封用户: {user_id}")
            return self._save_bans()
        return True
    
    def get_ban_list(self) -> List[dict]:
        """获取当前所有有效封禁列表"""
        result = []
        now = time.time()
        
        for key, (expire_at, reason) in self._temp_bans.items():
            if expire_at is None or expire_at > now:
                # 从 key 中解析出类型和值
                parts = key.split(':', 1)
                if len(parts) == 2:
                    target_type = parts[0]
                    # 注意：这里无法还原原始值，只能显示哈希后的值
                    # 实际使用时，可以在保存时额外存储原始值
                    result.append({
                        'type': target_type,
                        'hash': parts[1],
                        'reason': reason,
                        'expire_at': None if expire_at == float('inf') else datetime.fromtimestamp(expire_at).strftime('%Y-%m-%d %H:%M:%S'),
                        'is_permanent': expire_at == float('inf')
                    })
        
        return result
    
    def clear_expired(self):
        """清理过期的封禁"""
        now = time.time()
        expired_keys = [k for k, (exp, _) in self._temp_bans.items() 
                       if exp != float('inf') and exp <= now]
        for k in expired_keys:
            del self._temp_bans[k]
        
        if expired_keys:
            if self.log:
                self.log.info("system", f"清理了 {len(expired_keys)} 条过期封禁记录")
            self._save_bans()
    
    def is_ip_banned(self, ip: str) -> bool:
        """检查 IP 是否被封禁（便捷方法）"""
        banned, _ = self.check_banned("ip", ip)
        return banned
    
    def is_user_banned(self, user_id: str) -> bool:
        """检查用户是否被封禁（便捷方法）"""
        banned, _ = self.check_banned("user", user_id)
        return banned