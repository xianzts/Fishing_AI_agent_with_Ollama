from src.core import config
from src.core.security import Security
from src.db.db_services import DBServices

import logging

from collections import OrderedDict
from datetime import datetime, timedelta
from src.core import config

logger = logging.getLogger(__name__)  # 使用当前模块名创建 logger


class FakeLockCache:
    """
    记录"不存在的账号"的失败尝试，模拟锁定行为。
    只存在内存中，进程重启后自动清零，不会污染数据库。
    """

    def __init__(self, max_size=1000):
        # 用 OrderedDict 实现一个简单的 LRU，防止内存被恶意刷爆
        self._cache = OrderedDict()
        self._max_size = max_size

    def _evict(self):
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def is_locked(self, user_name):
        """检查该用户名是否处于假锁定状态"""
        info = self._cache.get(user_name)
        if not info:
            return False
        locked_until = info.get("locked_until")
        if locked_until and locked_until > datetime.utcnow():
            return True
        if locked_until:
            info["count"] = 0
            info["locked_until"] = None
        return False

    def record_failure(self, user_name):
        """记录一次失败，达到阈值则写入假锁定时间"""
        info = self._cache.get(user_name, {"count": 0, "locked_until": None})
        info["count"] += 1
        if info["count"] >= config.MAX_FAILED_ATTEMPTS:
            info["locked_until"] = datetime.utcnow() + timedelta(minutes=config.LOCK_DURATION_MINUTES)
        self._cache[user_name] = info
        # 每次写入后调整 LRU 顺序
        self._cache.move_to_end(user_name)
        self._evict()

    def clear(self, user_name):
        """账号在数据库中真实存在时，清除其假锁定记录"""
        self._cache.pop(user_name, None)


# ========== 全局单例，进程内所有请求共享 ==========
fake_lock_cache = FakeLockCache()
db_services = DBServices()


class UserAccount:
    def __init__(self, log_callback=None):
        self.log = log_callback or logger.info

    def confirm(self, user_name, password):
        # 1. 先检查假锁定（覆盖"账号不存在但被刷"的情况）
        if fake_lock_cache.is_locked(user_name):
            self.log(f"账号 {user_name} 处于假锁定状态")
            return None, {"remaining": 0, "locked": True}

        # 2. 查真实账号
        db_instance = DBServices()
        search_result = db_instance.search_account_with_pwd(user_name)
        if search_result is None:
            # 假帐号
            is_valid = Security().verify_user_password(password, Security().DUMMY_HASH)
            fake_lock_cache.record_failure(user_name)
            self.log(f"登录失败：账号不存在 {user_name}")
            info = fake_lock_cache._cache.get(user_name, {"count": 0})
            if info["count"] >= config.MAX_FAILED_ATTEMPTS:
                return None, {"remaining": 0, "locked": True}
            else:
                remaining = config.MAX_FAILED_ATTEMPTS - info["count"]
                return None, {"remaining": remaining, "locked": False}

        # --- 账号存在：走真实逻辑 ---
        # 存在则清掉假锁定记录（以防之前误记）
        fake_lock_cache.clear(user_name)

        # 3.检查真实锁定
        user_id, user_origin_password, failed_attempts, locked_until = search_result

        if locked_until is not None:
            if locked_until > datetime.utcnow():
                self.log(f"账号 {user_name} 已被锁定")
                return None, {"remaining": 0, "locked": True}
            else:
                # 锁定过期，重置计数
                db_services.reset_login_failure(user_id)
                failed_attempts = 0

        # 4.校验密码
        try:
            is_valid = Security().verify_user_password(password, user_origin_password)
        except ValueError as e:
            self.log(f"密码哈希校验失败: {e}")
            return None, None

        if is_valid:
            self.log(f"{user_name} 成功登录！")
            db_services.reset_login_failure(user_id)
            token = Security().jwt_token_generation(user_id, user_name)
            return {"access_token": token, "token_type": "bearer"}, None
        else:
            new_attempts = failed_attempts + 1
            if new_attempts >= config.MAX_FAILED_ATTEMPTS:
                lock_time = datetime.utcnow() + timedelta(minutes=config.LOCK_DURATION_MINUTES)
                db_services.record_login_failure(user_id, new_attempts, lock_time)
                self.log(f"账号 {user_name} 连续失败 {new_attempts} 次，已锁定")
                return None, {"remaining": 0, "locked": True}
            else:
                db_services.record_login_failure(user_id, new_attempts, None)
                remaining = config.MAX_FAILED_ATTEMPTS - new_attempts
                self.log(f"账号 {user_name} 密码错误，剩余尝试次数 {remaining} 次")
                return None, {"remaining": remaining, "locked": False}
