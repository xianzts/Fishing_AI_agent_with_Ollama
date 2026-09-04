from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

import logging

from src import config
from src.db_services import DBServices

logger = logging.getLogger(__name__)  # 使用当前模块名创建 logger


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

    def route_question(self, question: str) -> bool:
        """
        返回 True=需要RAG检索；False=跳过RAG，只用记忆+模型知识
        """
        prompt_text = config.ROUTER_PROMPT.format(question=question)
        resp = self.llm.invoke(prompt_text).content.strip()
        if resp not in ("USE_RAG", "SKIP_RAG"):
            return True
        return resp == "USE_RAG"

    def get_user_history(self, user_id, user_name) -> str:
        """获取格式化后的历史对话字符串，填入Prompt"""
        # connect to db to load the record
        db_instance = DBServices()
        res = db_instance.get_recent_chat_records(user_id)

        if not res["ok"]:
            err_code = res["err_code"]
            self.log(f"【警告】加载用户{user_name}对话历史失败，错误码:{err_code}")
            # 业务策略：SSE流式场景不中断整个问答，向大模型传入系统警告文本
            # 如果你希望异常直接中断请求，可以在这里raise异常交给上层路由处理
            return "[系统警告：用户历史对话因数据库故障无法加载]"

        search_result = res["data"]
        if len(search_result) == 0:
            # ✅ 正常查询，但是确实没有历史对话
            self.log(f"用户{user_name}暂无历史对话记录")
            return "无历史对话"

        out = []
        for question, answer in search_result:
            out.append(f"用户：{question}")
            out.append(f"助手：{answer}")

        self.log(f"加载用户{user_name}上下文成功，共{len(search_result)}轮对话")
        return "\n".join(out)

    def append_history(self, user_id, user_name, human_q: str, ai_a: str):
        """完成一轮问答之后调用，把问答存入记忆，自动裁剪旧对话"""
        self.log("正在保存当前对话QA")
        db_instance = DBServices()
        success = db_instance.add_chat_record_with_cleanup(user_id, human_q, ai_a)
        if success:
            self.log("对话历史更新成功")
        else:
            self.log("对话历史更新失败")

    def stream_answer(self, user_id, user_name, question: str, retriever):
        need_retrieve = self.route_question(question)

        context_text = ""
        if need_retrieve:
            self.log("问题：{} -> 需要检索知识库".format(question))
            good_docs = retriever.invoke(question)
            context_text = "\n".join([d.page_content for d in good_docs])
            self.log("知识库检索数量：{}".format(len(good_docs)))
        else:
            self.log("问题：{} -> 不需要检索知识库".format(question))

        chat_history = self.get_user_history(user_id, user_name)

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
        db_instance = DBServices()
        self.log("正在清理所有历史记录")
        if db_instance.clean_records(user_id):
            self.log("历史记录清理成功")
        else:
            self.log("历史记录清理失败")
