from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

import logging
import pymysql

from src import config

logger = logging.getLogger(__name__)   # 使用当前模块名创建 logger


class LLMServices:
    def __init__(self, log_callback=None):
        self.llm = ChatOllama(model=config.AGENT_MODEL,
                              base_url=config.URL,
                              temperature=config.TEMP
                              )

        # 内存存储会话记忆 key:用户名，value 一轮轮对话列表
        self.session_memory = {}
        self.max_turn = config.MAX_TURN  # 最多保存最近6轮问答，防止prompt爆炸
        self.log = log_callback or logger.info

    def db_conn(self):
        try:
            conn = pymysql.connect(**config.DB)
            self.log("数据库连接成功")

        except pymysql.err.OperationalError as e:
            self.log(f"数据库连接失败: {e}")

        return conn

    def route_question(self, question: str) -> bool:
        """
        返回 True=需要RAG检索；False=跳过RAG，只用记忆+模型知识
        """
        prompt_text = config.ROUTER_PROMPT.format(question=question)
        resp = self.llm.invoke(prompt_text).content.strip()
        if resp not in ("USE_RAG", "SKIP_RAG"):
            return True
        return resp == "USE_RAG"

    def get_user_history(self, user_id) -> str:
        """获取格式化后的历史对话字符串，填入Prompt"""

        # connect to db to load the record
        self.log("正在连接数据库")
        conn = self.db_conn()

        cursor = None
        try:
            cursor = conn.cursor()
            sql = "SELECT question, answer FROM user_record WHERE user_id = %s"
            cursor.execute(sql, (user_id,))

            search_result = cursor.fetchone()
            if search_result is None:
                return "无历史对话"

            out = []
            for i in range(len(search_result)):
                if i % 2 == 0:
                    out.append(f"用户：{search_result[i]}")
                else:
                    out.append(f"助手：{search_result[i]}")

            self.log(f"加载用户上下文成功")
            return "\n".join(out)

        except pymysql.err.OperationalError as e:
            self.log(f"加载用户上下文失败: {e}")
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

    def append_history(self, user_id, user_name, human_q: str, ai_a: str):
        """完成一轮问答之后调用，把问答存入记忆，自动裁剪旧对话"""
        # connect to db to add the record
        self.log("正在连接数据库")
        conn = self.db_conn()

        cursor = None
        try:
            cursor = conn.cursor()
            sql = "INSERT INTO user_record (user_id, question, answer) VALUES (%s, %s, %s)"
            cursor.execute(sql, (user_id, human_q, ai_a))

            sql = "SELECT count(*) FROM user_record WHERE user_id = %s"
            cursor.execute(sql, (user_id,))

            search_result = cursor.fetchone()
            record_count = search_result[0]

            if record_count > config.MAX_TURN:
                self.log("已检测到超过{}条记录，正在删除旧纪录".format(config.MAX_TURN))
                sql = "SELECT * FROM user_record WHERE user_id = %s ORDER BY create_time ASC LIMIT 1"
                cursor.execute(sql, (user_id,))

                search_result = cursor.fetchone()
                record_id = search_result[0]

                sql = "DELETE FROM user_record WHERE id = %s"
                cursor.execute(sql, (record_id,))
                self.log("旧纪录删除成功")

            conn.commit()

            self.log(f"用户 {user_name} 对话保存成功")

        except pymysql.err.OperationalError as e:
            self.log(f"用户 {user_name} 对话保存失败: {e}")
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

    def stream_answer(self, user_name, user_id, question: str, retriever):
        need_retrieve = self.route_question(question)

        context_text = ""
        if need_retrieve:
            self.log("问题：{} -> 需要检索知识库".format(question))
            good_docs = retriever.invoke(question)
            context_text = "\n".join([d.page_content for d in good_docs])
            self.log("知识库检索数量：{}".format(len(good_docs)))
        else:
            self.log("问题：{} -> 不需要检索知识库".format(question))

        chat_history = self.get_user_history(user_id)

        prompt = config.SYSTEM_PROMPT.format(
            username=user_name,
            context=context_text if context_text else config.NO_CONTENT,
            history=chat_history
        )

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=question)
        ]
        stream_generator = self.llm.stream(messages)
        return stream_generator

    def clear_history(self, user_id):
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
