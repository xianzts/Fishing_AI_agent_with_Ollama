from passlib.hash import bcrypt
import pymysql
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError, DecodeError

from src import config
from src.db_services import DBServices

import logging

logger = logging.getLogger(__name__)   # 使用当前模块名创建 logger


class UserAccount:
    def __init__(self, log_callback=None):
        self.log = log_callback or logger.info

    def secret_generation(self):
        # 生成64位长度，适配 HS256 / HS512 JWT算法
        jwt_secret = secrets.token_urlsafe(config.SECRET_KEY_LENGTH)
        self.log(jwt_secret)

    def jwt_token_generation(self, user_id: int, username: str) -> str:
        """生成JWT token"""
        expire = datetime.now(timezone.utc) + config.ACCESS_TOKEN_EXPIRES
        payload = {
            "user_id": str(user_id),
            "username": username,
            "iat": datetime.now(timezone.utc),
            "exp": expire
        }
        token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
        return token

    def verify_access_token(self, token: str):
        """
        校验并解析token
        返回字典 {"user_id":xxx, "username":xxx}；校验失败返回None
        """
        try:
            payload = jwt.decode(
                token,
                config.JWT_SECRET_KEY,
                algorithms=[config.JWT_ALGORITHM],
                options={"verify_exp": True}  # 开启过期校验
            )

            return {
                "user_id": payload["user_id"],
                "username": payload["username"],
                "issue_at": payload["iat"],
                "expire": payload["exp"]
            }
        except ExpiredSignatureError:
            self.log("token已经过期")
            return None
        except InvalidSignatureError:
            self.log("签名错误，token被篡改或者密钥错误")
            return None
        except DecodeError:
            self.log("token格式损坏")
            return None
        except Exception as e:
            self.log(f"token校验异常: {e}")
            return None

    def confirm(self, user_name, password):
        db_instance = DBServices()
        search_result = db_instance.search_account_with_pwd(user_name)
        if search_result is None:
            self.log("账号或密码错误，请重新输入！")
            return None

        user_id, user_origin_password = search_result
        try:
            is_valid = bcrypt.verify(password, user_origin_password)
        except ValueError as e:
            self.log(f"密码哈希校验失败: {e}")
            return None

        if is_valid:
            self.log(f"{user_name} 成功登录！")
            token = self.jwt_token_generation(user_id, user_name)
            return {"access_token": token, "token_type": "bearer"}
        else:
            self.log("账号或密码错误，请重新输入！")
            return None
