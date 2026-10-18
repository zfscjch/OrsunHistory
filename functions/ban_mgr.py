import os
import json
import time
import uuid
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Tuple, List

try:
    import fcntl  # Unix only
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

from .log import LogMgr


def _looks_like_hash(value: str) -> bool:
    """判断是否为 32 位十六进制串（用于兼容旧数据的 hash 解封）"""
    if not isinstance(value, str) or len(value) != 32:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


class BanMgr:
    """封禁管理器

    存储：文件 + 内存缓存
    并发：threading.RLock（内存） + fcntl.flock（文件写） + 原子 replace
    多进程：通过 mtime 检测外部修改，实现最终一致
    """

    BAN_FILE = os.path.join(os.path.dirname(__file__), 'db', 'bans.json')

    def __init__(self, log_mgr: Optional[LogMgr] = None):
        self.log = log_mgr or LogMgr("../logs/OrsunHistory/ban.log")
        self._lock = threading.RLock()
        self._bans = {}            # key -> record dict
        self._file_mtime_ns = None
        os.makedirs(os.path.dirname(self.BAN_FILE), exist_ok=True)
        self._load_bans()

    # ------------------------------------------------------------------ #
    # 锁
    # ------------------------------------------------------------------ #
    @contextmanager
    def _write_lock(self):
        """跨进程写锁（仅 Unix 生效）"""
        lock_path = self.BAN_FILE + '.lock'
        fh = open(lock_path, 'a+')
        try:
            if _HAS_FCNTL:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            if _HAS_FCNTL:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            fh.close()

    # ------------------------------------------------------------------ #
    # 加载 / 保存
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_record(key: str, rec: dict) -> dict:
        target_type = rec.get('target_type')
        if not target_type:
            target_type = key.split(':', 1)[0] if ':' in key else 'unknown'
        return {
            'id': key,
            'target_type': target_type,
            'target_value': rec.get('target_value'),  # 旧数据为 None
            'reason': rec.get('reason') or '',
            'banned_by': rec.get('banned_by') or 'system',
            'created_at': rec.get('created_at'),
            'expire_at': rec.get('expire_at'),
        }

    def _load_bans_inner(self):
        """假定已持有 self._lock；用 fstat 保证内容与 mtime 一致"""
        try:
            if not os.path.exists(self.BAN_FILE):
                self._bans = {}
                self._file_mtime_ns = None
                return
            with open(self.BAN_FILE, 'rb') as f:
                st = os.fstat(f.fileno())
                raw = json.load(f)
            bans = {}
            if isinstance(raw, dict):
                for key, rec in raw.items():
                    if not isinstance(rec, dict):
                        continue
                    bans[key] = self._normalize_record(key, rec)
            self._bans = bans
            self._file_mtime_ns = st.st_mtime_ns
        except Exception as e:
            self._bans = {}
            self._file_mtime_ns = None
            if self.log:
                self.log.error("system", f"加载封禁数据失败: {e}", "127.0.0.1")

    def _load_bans(self):
        with self._lock:
            self._load_bans_inner()

    def _maybe_reload(self):
        """假定已持有 self._lock；若文件被其他进程修改则重新加载"""
        try:
            mtime_ns = os.stat(self.BAN_FILE).st_mtime_ns
        except OSError:
            return
        if mtime_ns != self._file_mtime_ns:
            self._load_bans_inner()

    def _save_inner(self) -> bool:
        """假定已持有 self._lock（及写锁）；原子写"""
        try:
            data = {}
            for key, rec in self._bans.items():
                data[key] = {
                    'target_type': rec.get('target_type'),
                    'target_value': rec.get('target_value'),
                    'reason': rec.get('reason') or '',
                    'banned_by': rec.get('banned_by') or 'system',
                    'created_at': rec.get('created_at'),
                    'expire_at': rec.get('expire_at'),
                }
            dir_path = os.path.dirname(self.BAN_FILE)
            fd, tmp = tempfile.mkstemp(dir=dir_path, prefix='.bans_', suffix='.tmp')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.BAN_FILE)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
            self._file_mtime_ns = os.stat(self.BAN_FILE).st_mtime_ns
            return True
        except Exception as e:
            if self.log:
                self.log.error("system", f"保存封禁数据失败: {e}", "127.0.0.1")
            return False

    # ------------------------------------------------------------------ #
    # 查找
    # ------------------------------------------------------------------ #
    def _find_key_by_value(self, target_type: str, target_value: str) -> Optional[str]:
        for key, rec in self._bans.items():
            if rec.get('target_type') == target_type and rec.get('target_value') == target_value:
                return key
        return None

    def _find_key_by_hash(self, target_type: str, hash_value: str) -> Optional[str]:
        for key, rec in self._bans.items():
            if rec.get('target_type') != target_type:
                continue
            suffix = key.split(':', 1)[1] if ':' in key else key
            if suffix == hash_value:
                return key
        return None

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def check_banned(self, target_type: str, target_value: str) -> Tuple[bool, Optional[str]]:
        if not target_value:
            return False, None
        with self._lock:
            self._maybe_reload()
            key = self._find_key_by_value(target_type, target_value)
            if key is None:
                return False, None
            rec = self._bans[key]
            expire_at = rec.get('expire_at')
            if expire_at is None or expire_at > time.time():
                return True, rec.get('reason')
            return False, None

    def get_ban_list(self, include_expired: bool = True) -> List[dict]:
        """返回封禁列表（默认包含已过期，便于审计）"""
        now = time.time()
        result = []
        with self._lock:
            self._maybe_reload()
            for key, rec in self._bans.items():
                expire_at = rec.get('expire_at')
                if expire_at is None:
                    status = 'permanent'
                    expire_str = None
                elif expire_at > now:
                    status = 'active'
                    expire_str = datetime.fromtimestamp(expire_at).isoformat(timespec='seconds')
                else:
                    status = 'expired'
                    expire_str = datetime.fromtimestamp(expire_at).isoformat(timespec='seconds')
                if not include_expired and status == 'expired':
                    continue
                created_at = rec.get('created_at')
                result.append({
                    'id': key,
                    'type': rec.get('target_type'),
                    'target': rec.get('target_value'),
                    'hash': key.split(':', 1)[1] if ':' in key else key,
                    'reason': rec.get('reason'),
                    'banned_by': rec.get('banned_by') or 'system',
                    'created_at': datetime.fromtimestamp(created_at).isoformat(timespec='seconds')
                    if created_at else None,
                    'expire_at': expire_str,
                    'status': status,
                    'is_permanent': status == 'permanent',
                    'is_active': status in ('active', 'permanent'),
                })
        active = [x for x in result if x['status'] != 'expired']
        expired = [x for x in result if x['status'] == 'expired']
        active.sort(key=lambda x: x['created_at'] or '', reverse=True)
        expired.sort(key=lambda x: x['created_at'] or '', reverse=True)
        return active + expired

    # ------------------------------------------------------------------ #
    # 封禁
    # ------------------------------------------------------------------ #
    def ban(self, target_type: str, target_value: str, reason: str,
            duration_seconds: Optional[int] = None, banned_by: str = "system") -> bool:
        if not target_value:
            return False
        now = time.time()
        expire_at = None if duration_seconds is None else now + duration_seconds
        with self._lock:
            with self._write_lock():
                self._load_bans_inner()  # 写前 reload，避免 lost update
                key = self._find_key_by_value(target_type, target_value)
                if key is None:
                    key = f"{target_type}:{uuid.uuid4().hex}"
                self._bans[key] = {
                    'id': key,
                    'target_type': target_type,
                    'target_value': target_value,
                    'reason': reason or '',
                    'banned_by': banned_by,
                    'created_at': now,
                    'expire_at': expire_at,
                }
                ok = self._save_inner()
        duration_str = "永久" if duration_seconds is None else f"{duration_seconds}秒"
        if self.log:
            self.log.info(banned_by,
                          f"封禁{target_type}: {target_value}, 原因: {reason}, 时长: {duration_str}",
                          "127.0.0.1")
        return ok

    def ban_ip(self, ip: str, reason: str, duration_seconds: Optional[int] = None,
               banned_by: str = "system") -> bool:
        return self.ban("ip", ip, reason, duration_seconds, banned_by)

    def ban_user(self, user_id: str, reason: str, duration_seconds: Optional[int] = None,
                 banned_by: str = "system") -> bool:
        return self.ban("user", user_id, reason, duration_seconds, banned_by)

    # ------------------------------------------------------------------ #
    # 解封
    # ------------------------------------------------------------------ #
    def unban(self, target_type: str, target_value: str) -> bool:
        if not target_value:
            return False
        with self._lock:
            with self._write_lock():
                self._load_bans_inner()
                key = self._find_key_by_value(target_type, target_value)
                matched_by = 'value'
                if key is None and _looks_like_hash(target_value):
                    # 兼容旧数据：前端可能传 hash
                    key = self._find_key_by_hash(target_type, target_value)
                    matched_by = 'hash'
                if key is None:
                    return False
                self._bans.pop(key, None)
                ok = self._save_inner()
        if ok and self.log:
            self.log.info("system",
                          f"解封{target_type}: {target_value} (匹配方式: {matched_by})",
                          "127.0.0.1")
        return ok

    def unban_ip(self, ip: str) -> bool:
        return self.unban("ip", ip)

    def unban_user(self, user_id: str) -> bool:
        return self.unban("user", user_id)

    # ------------------------------------------------------------------ #
    # 清理
    # ------------------------------------------------------------------ #
    def clear_expired(self) -> int:
        now = time.time()
        with self._lock:
            with self._write_lock():
                self._load_bans_inner()
                expired_keys = [
                    k for k, rec in self._bans.items()
                    if rec.get('expire_at') is not None and rec['expire_at'] <= now
                ]
                if not expired_keys:
                    return 0
                for k in expired_keys:
                    self._bans.pop(k, None)
                self._save_inner()
        if self.log:
            self.log.info("system", f"清理了 {len(expired_keys)} 条过期封禁记录", "127.0.0.1")
        return len(expired_keys)

    # ------------------------------------------------------------------ #
    # 便捷方法
    # ------------------------------------------------------------------ #
    def is_ip_banned(self, ip: str) -> bool:
        return self.check_banned("ip", ip)[0]

    def is_user_banned(self, user_id: str) -> bool:
        return self.check_banned("user", user_id)[0]
