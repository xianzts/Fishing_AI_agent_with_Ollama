from src.core import config
from src.core.security import Security
from src.db.db_services import DBServices

import logging

logger = logging.getLogger(__name__)   # 使用当前模块名创建 logger


class UserAccount:
    def __init__(self, log_callback=None):
        self.log = log_callback or logger.info

    def confirm(self, user_name, password):
        db_instance = DBServices()
        search_result = db_instance.search_account_with_pwd(user_name)
        if search_result is None:
            self.log("账号或密码错误，请重新输入！")
            return None

        user_id, user_origin_password = search_result
        try:
            is_valid = Security().verify_user_password(password, user_origin_password)
        except ValueError as e:
            self.log(f"密码哈希校验失败: {e}")
            return None

        if is_valid:
            self.log(f"{user_name} 成功登录！")
            token = Security().jwt_token_generation(user_id, user_name)
            return {"access_token": token, "token_type": "bearer"}
        else:
            self.log("账号或密码错误，请重新输入！")
            return None
