import pymysql
import re
from passlib.hash import bcrypt
import logging

from src import config

logger = logging.getLogger(__name__)   # 使用当前模块名创建 logger


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

    def add_chat_record_with_cleanup(self, user_id, question, answer, max_keep=config.MAX_TURN):
        """保存一轮对话，并自动清理该用户最旧的记录，保证总数不超过 max_keep。
        使用同一事务，要么全部成功，要么全部回滚。"""
        self.log("正在连接数据库")
        conn = self.db_conn()
        cursor = None

        try:
            if not conn or not conn.open:
                return False

            cursor = conn.cursor()

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
            conn.commit()
            self.log("对话保存及清理成功")
            return True

        except pymysql.err.IntegrityError as e:
            self.log(f"保存对话失败（唯一键冲突）: {e}")
            conn.rollback()
            return False
        except pymysql.MySQLError as e:
            self.log(f"保存对话失败: {e}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_recent_chat_records(self, user_id):
        self.log("正在连接数据库")
        conn = self.db_conn()
        cursor = None

        try:
            if not conn or not conn.open:
                return False

            cursor = conn.cursor()
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
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

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

    def search_account_with_pwd(self, user_name):
        self.log("正在连接数据库")
        conn = self.db_conn()

        cursor = None
        try:
            cursor = conn.cursor()
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
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def clean_records(self, user_id):
        # connect to db to delete the record
        self.log("正在连接数据库")
        conn = self.db_conn()

        cursor = None
        try:
            cursor = conn.cursor()
            sql = "DELETE FROM user_record WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            conn.commit()
            self.log(f"清除上下文成功")
            return True

        except pymysql.err.OperationalError as e:
            self.log(f"清除上下文失败: {e}")
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
