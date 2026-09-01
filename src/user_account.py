from passlib.hash import bcrypt
import pymysql
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError, DecodeError

from src import config

import logging

logger = logging.getLogger(__name__)   # 使用当前模块名创建 logger


class UserAccount:
    def __init__(self, log_callback=None):
        self.user_origin_password = ""
        self.user_name = 'unknown'
        self.id = None
        self.log = log_callback or logger.info

    def secret_generation(self):
        # 生成64位长度，适配 HS256 / HS512 JWT算法
        jwt_secret = secrets.token_urlsafe(config.SECRET_KEY_LENGTH)
        self.log(jwt_secret)

    def jwt_token_generation(self, user_id: int, username: str) -> str:
        """生成JWT token"""
        expire = datetime.now(timezone.utc) + timedelta(seconds=config.ACCESS_TOKEN_EXPIRE_SECONDS)
        payload = {
            "sub": str(user_id),
            "username": username,
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
                "user_id": payload["sub"],
                "username": payload["username"]
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

    def db_conn(self):
        try:
            conn = pymysql.connect(**config.DB)
            self.log("数据库连接成功")

        except pymysql.err.OperationalError as e:
            self.log(f"数据库连接失败: {e}")

        return conn

    def register_account(self, user_name, password):
        self.log("正在连接数据库")
        conn = self.db_conn()
        cursor = None
        try:
            cursor = conn.cursor()
            pwd_hash = bcrypt.hash(password)
            sql = "INSERT INTO account (username, pwd_hash) VALUES (%s, %s)"
            cursor.execute(sql, (user_name, pwd_hash))
            conn.commit()
            self.log(f"用户 {user_name} 注册成功")
            return True
        except pymysql.err.IntegrityError as e:
            # 唯一键冲突（例如用户名已存在）
            self.log(f"注册失败，用户名已存在: {user_name} - {e}")
            conn.rollback()
            return False
        except pymysql.err.OperationalError as e:
            # 连接问题、SQL执行错误等
            self.log(f"数据库操作错误: {e}")
            conn.rollback()
            return False
        except pymysql.MySQLError as e:
            # 其他 MySQL 相关异常
            self.log(f"数据库未知错误: {e}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def confirm(self, user_name, password):
        self.user_name = user_name

        self.log("正在连接数据库")
        conn = self.db_conn()

        cursor = None
        try:
            cursor = conn.cursor()
            sql = "SELECT id, pwd_hash FROM account WHERE username = %s"
            cursor.execute(sql, (user_name,))
            search_result = cursor.fetchone()

            if search_result is None:
                self.log("账号或密码错误，请重新输入！")
                return None
            else:
                self.id, self.user_origin_password = search_result
                try:
                    is_valid = bcrypt.verify(password, self.user_origin_password)
                except ValueError as e:
                    self.log(f"密码哈希校验失败: {e}")
                    return None

                if is_valid:
                    self.log(f"{self.user_name} 成功登录！")
                    token = self.jwt_token_generation(self.id, self.user_name)
                    return {"access_token": token, "token_type": "bearer"}
                else:
                    self.log("账号或密码错误，请重新输入！")
                    return None

        except pymysql.err.OperationalError as e:
            self.log(f"账号查询失败: {e}")
            return None
        except pymysql.MySQLError as e:
            # 捕获其他未预料的数据库异常
            self.log(f"数据库未知错误: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
