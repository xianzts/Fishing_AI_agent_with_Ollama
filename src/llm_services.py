from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

import logging

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

    def route_question(self, question: str) -> bool:
        """
        返回 True=需要RAG检索；False=跳过RAG，只用记忆+模型知识
        """
        prompt_text = config.ROUTER_PROMPT.format(question=question)
        resp = self.llm.invoke(prompt_text).content.strip()
        if resp not in ("USE_RAG", "SKIP_RAG"):
            return True
        return resp == "USE_RAG"

    def get_user_history(self, user_name: str) -> str:
        """获取格式化后的历史对话字符串，填入Prompt"""
        if user_name not in self.session_memory:
            return "无历史对话"
        turn_list = self.session_memory[user_name]
        out = []
        for human, ai in turn_list:
            out.append(f"用户：{human}")
            out.append(f"助手：{ai}")
        return "\n".join(out)

    def append_history(self, user_name: str, human_q: str, ai_a: str):
        """完成一轮问答之后调用，把问答存入记忆，自动裁剪旧对话"""
        if user_name not in self.session_memory:
            self.session_memory[user_name] = []
        self.session_memory[user_name].append((human_q, ai_a))
        # 只保留最近N轮，删掉最旧的
        if len(self.session_memory[user_name]) > self.max_turn:
            self.session_memory[user_name].pop(0)

    def stream_answer(self, user_name, question: str, retriever):
        need_retrieve = self.route_question(question)

        context_text = ""
        if need_retrieve:
            self.log("问题：{}，需要检索知识库".format(question))
            good_docs = retriever.invoke(question)
            context_text = "\n".join([d.page_content for d in good_docs])
            self.log("检索数量：{}".format(len(good_docs)))
        else:
            self.log("问题：{}，不需要检索知识库".format(question))

        chat_history = self.get_user_history(user_name)

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

    def clear_history(self, user_name: str):
        self.session_memory[user_name].clear()
        self.log("上下文记忆清空成功")
