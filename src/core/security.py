from passlib.hash import bcrypt
import secrets
import logging
import jwt
from datetime import datetime, timedelta, timezone
from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError, DecodeError

from src.core import config

logger = logging.getLogger(__name__)  # 使用当前模块名创建 logger


class Security:
    def __init__(self, log_callback=None):
        self.log = log_callback or logger.info
        self.DUMMY_HASH = bcrypt.hash(b"dummy_password_for_timing_xianztsying")

    def get_hash_pwd(self, password: str):
        try:
            hash_pwd = bcrypt.hash(password)
            self.log("密码哈希成功")
        except Exception as e:
            self.log(f"密码哈希失败: {e}")
        return hash_pwd

    def verify_user_password(self, password, user_origin_password):
        is_valid = bcrypt.verify(password, user_origin_password)
        self.log("密码校验完成")
        return is_valid

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



