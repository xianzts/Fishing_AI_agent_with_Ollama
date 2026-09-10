import pymysql
import re
import logging
from passlib.hash import bcrypt
from contextlib import contextmanager

from src.core import config

logger = logging.getLogger(__name__)  # 使用当前模块名创建 logger


class DBServices:
    def __init__(self, log_callback=None):
        self.log = log_callback or logger.info

    def db_conn(self):
        try:
            conn = pymysql.connect(**config.DB)
            self.log("数据库连接成功")

        except pymysql.err.OperationalError as e:
            self.log(f"数据库连接失败: {e}")

        return conn

    @contextmanager
    def get_cursor(self):
        self.log("正在连接数据库")
        conn = self.db_conn()
        cursor = conn.cursor()
        try:
            yield cursor, conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def add_chat_record_with_cleanup(self, user_id, question, answer, max_keep=config.MAX_TURN):
        """保存一轮对话，并自动清理该用户最旧的记录，保证总数不超过 max_keep。
        使用同一事务，要么全部成功，要么全部回滚。"""
        try:
            with self.get_cursor() as (cursor, conn):
                # 1. 插入新记录
                sql_insert = "INSERT INTO user_record (user_id, question, answer) VALUES (%s, %s, %s)"
                cursor.execute(sql_insert, (user_id, question, answer))

                # 2. 清理旧记录（如果需要）
                sql_count = "SELECT COUNT(*) FROM user_record WHERE user_id = %s"
                cursor.execute(sql_count, (user_id,))
                total = cursor.fetchone()[0]

                if total > max_keep:
                    excess = total - max_keep
                    sql_old_ids = """
                        SELECT id FROM user_record 
                        WHERE user_id = %s 
                        ORDER BY create_time ASC 
                        LIMIT %s
                    """
                    cursor.execute(sql_old_ids, (user_id, excess))
                    ids = [row[0] for row in cursor.fetchall()]

                    if ids:
                        format_strings = ','.join(['%s'] * len(ids))
                        sql_delete = f"DELETE FROM user_record WHERE id IN ({format_strings})"
                        cursor.execute(sql_delete, tuple(ids))
                        self.log(f"已删除 {len(ids)} 条旧记录")

                # 所有操作成功，统一提交
                self.log("对话保存及清理成功")
                return True

        except pymysql.err.IntegrityError as e:
            self.log(f"保存对话失败（唯一键冲突）: {e}")
            return False
        except pymysql.MySQLError as e:
            self.log(f"保存对话失败: {e}")
            return False

    def get_recent_chat_records(self, user_id):
        try:
            with self.get_cursor() as (cursor, conn):
                sql = "SELECT question, answer FROM user_record WHERE user_id = %s"
                cursor.execute(sql, (user_id,))

                search_result = cursor.fetchall()
                self.log(f"查询用户历史记录成功")
                return {"ok": True, "data": list(search_result)}

        except pymysql.err.OperationalError as e:
            self.log(f"查询用户历史记录失败: {e}")
            return {"ok": False, "err_code": "DB_QUERY_FAIL", "data": None}
        except pymysql.MySQLError as e:
            # 捕获其他未预料的数据库异常
            self.log(f"数据库未知错误: {e}")
            return {"ok": False, "err_code": "UNKNOWN", "data": None}

    def register_account(self, user_name, password):
        try:
            with self.get_cursor() as (cursor, conn):
                pwd_hash = bcrypt.hash(password)
                sql = "INSERT INTO account (username, pwd_hash) VALUES (%s, %s)"
                cursor.execute(sql, (user_name, pwd_hash))

                self.log(f"用户 {user_name} 注册成功")
                return True
        except pymysql.err.IntegrityError as e:
            # 唯一键冲突（例如用户名已存在）
            self.log(f"注册失败，用户名已存在: {user_name} - {e}")
            return False
        except pymysql.err.OperationalError as e:
            # 连接问题、SQL执行错误等
            self.log(f"数据库操作错误: {e}")
            return False
        except pymysql.MySQLError as e:
            # 其他 MySQL 相关异常
            self.log(f"数据库未知错误: {e}")
            return False

    def search_account_with_pwd(self, user_name):
        try:
            with self.get_cursor() as (cursor, conn):
                sql = "SELECT id, pwd_hash FROM account WHERE username = %s"
                cursor.execute(sql, (user_name,))

                search_result = cursor.fetchone()
                self.log(f"数据库查询成功")
                return search_result

        except pymysql.err.OperationalError as e:
            self.log(f"账号查询失败: {e}")
            return None
        except pymysql.MySQLError as e:
            # 捕获其他未预料的数据库异常
            self.log(f"数据库未知错误: {e}")
            return None

    def clean_records(self, user_id):
        # connect to db to delete the record
        try:
            with self.get_cursor() as (cursor, conn):
                sql = "DELETE FROM user_record WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                self.log(f"清除上下文成功")
                return True

        except pymysql.err.OperationalError as e:
            self.log(f"清除上下文失败: {e}")
            return False
        except pymysql.MySQLError as e:
            # 捕获其他未预料的数据库异常
            self.log(f"数据库未知错误: {e}")
            return False
