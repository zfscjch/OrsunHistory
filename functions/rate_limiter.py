import os
import json
import time
from typing import Dict, List

# 请求计数存储路径
RATE_LIMIT_FILE = os.path.join(os.path.dirname(__file__), 'db', 'rate_limits.json')

# 默认限流配置 (次数/分钟)
RATE_LIMITS = {
    '/api/': 30,      # API 接口 30次/分钟
    '/forum/': 20,    # 论坛 20次/分钟
    '/chat': 60,      # 聊天 60次/分钟
    '/admin/': 10,    # 管理员接口 10次/分钟
    'default': 60,    # 默认 60次/分钟
}

# IP 黑名单（手动添加的恶意 IP）
IP_BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), 'db', 'ip_blacklist.json')


def _load_rate_data() -> Dict:
    """加载请求计数数据"""
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def _save_rate_data(data: Dict):
    """保存请求计数数据"""
    try:
        with open(RATE_LIMIT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except:
        pass


def _load_ip_blacklist() -> List[str]:
    """加载 IP 黑名单"""
    if os.path.exists(IP_BLACKLIST_FILE):
        try:
            with open(IP_BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return []


def _save_ip_blacklist(blacklist: List[str]):
    """保存 IP 黑名单"""
    try:
        with open(IP_BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, indent=2)
    except:
        pass


def check_rate_limit(ip: str, path: str, window_seconds: int = 60) -> bool:
    """
    检查频率限制
    返回 True 允许访问，False 触发限流
    """
    # 首先检查 IP 是否在黑名单中
    if ip in _load_ip_blacklist():
        return False
    
    now = time.time()
    data = _load_rate_data()
    
    # 确定限流阈值
    limit = RATE_LIMITS.get('default', 60)
    for prefix, l in RATE_LIMITS.items():
        if path.startswith(prefix):
            limit = l
            break
    
    # 生成 key（按分钟和路径分组）
    minute_key = int(now / 60)  # 按分钟分组
    key = f"{ip}:{path}:{minute_key}"
    
    # 获取当前分钟的请求计数
    count = data.get(key, 0)
    
    # 检查是否超过限制
    if count >= limit:
        # 自动加入黑名单（连续超过限制）
        if count >= limit * 3:  # 超过限制3倍，加入黑名单
            blacklist = _load_ip_blacklist()
            if ip not in blacklist:
                blacklist.append(ip)
                _save_ip_blacklist(blacklist)
        return False
    
    # 记录本次请求
    data[key] = count + 1
    
    # 清理过期的 key（超过10分钟未更新的）
    current_minute = int(now / 60)
    expired_keys = [k for k in data.keys() 
                   if not k.endswith(path) or not all(p.isdigit() for p in k.split(':')[-1].split())]
    # 简化清理：只保留最近10分钟的数据
    data = {k: v for k, v in data.items() 
            if int(k.split(':')[-1]) > current_minute - 10}
    
    _save_rate_data(data)
    return True


def add_ip_blacklist(ip: str) -> bool:
    """手动添加 IP 到黑名单"""
    blacklist = _load_ip_blacklist()
    if ip not in blacklist:
        blacklist.append(ip)
        _save_ip_blacklist(blacklist)
        return True
    return False


def remove_ip_blacklist(ip: str) -> bool:
    """从 IP 黑名单中移除"""
    blacklist = _load_ip_blacklist()
    if ip in blacklist:
        blacklist.remove(ip)
        _save_ip_blacklist(blacklist)
        return True
    return False