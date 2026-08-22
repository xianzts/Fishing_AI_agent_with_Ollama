from passlib.hash import bcrypt
import pymysql

import config


class UserAccount:
    def __init__(self, log_callback=None):
        self.user_origin_password = ""
        self.user_name = 'unknown'
        self.log = log_callback or print

    def db_conn(self):
        try:
            conn = pymysql.connect(**config.DB)

        except pymysql.err.OperationalError as e:
            self.log(f"数据库连接失败: {e}")

        return conn

    def register_account(self, user_name, password):
        conn = self.db_conn()
        if conn.open:
            cursor = conn.cursor()
            sql = "INSERT INTO account (username, pwd_hash) VALUES (%s, %s)"
            pwd_hash = bcrypt.hash(password)

            try:
                cursor.execute(sql, (user_name, pwd_hash))
                conn.commit()
                return True
            except pymysql.err.OperationalError as e:
                self.log(f"账号注册失败: {e}")
                return False
            finally:
                cursor.close()
                conn.close()

    def confirm(self, user_name, password):
        self.user_name = user_name

        conn = self.db_conn()
        if conn.open:
            cursor = conn.cursor()
            sql = "SELECT pwd_hash FROM account WHERE username = %s"

            try:
                cursor.execute(sql, (user_name,))
                search_result = cursor.fetchone()

                if search_result is None:
                    self.log("该账号不存在！")
                    return False
                else:
                    self.user_origin_password = search_result[0]
                    if bcrypt.verify(password, self.user_origin_password):
                        self.log("{} 成功登录！".format(user_name))
                        return True
                    else:
                        self.log("账号或密码错误，请重新输入！")

            except pymysql.err.OperationalError as e:
                self.log(f"账号查询失败: {e}")
                return False
            finally:
                cursor.close()
                conn.close()


