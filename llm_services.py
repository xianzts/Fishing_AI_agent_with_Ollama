from langchain_ollama import ChatOllama
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

import config


class LLMServices:
    def __init__(self):
        llm = ChatOllama(model=config.AGENT_MODEL,
                         base_url=config.URL,
                         temperature=config.TEMP
                         )
        prompt = ChatPromptTemplate.from_messages([
            ("system", config.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

        self.chat_history = ChatMessageHistory()
        self.chat_chain = prompt | llm

        self.memory = RunnableWithMessageHistory(
            self.chat_chain,
            lambda session_id: self.chat_history,
            input_messages_key="input",
            history_messages_key="history"
        )

    def stream_answer(self, user_name, question: str, retriever):
        # 检索知识库
        related_docs = retriever.invoke(question)
        context = "\n====\n".join([doc.page_content for doc in related_docs])

        # RAG提示词：强制模型只能使用知识库上下文，抑制幻觉
        prompt = f"""
    【知识库上下文】
    {context}
    当前用户信息：{user_name}

    用户问题：{question}
    
    回答规则：
    1. 如果参考知识库有相关内容，优先参考知识库；
    2. 如果知识库没有信息，**去查看下方对话历史获取答案**（比如用户名字、刚刚聊过的话题）；
    3. 用户问：知道我的名字吗？ 直接从【当前用户信息】或者对话历史读取名字，不要去知识库查找；
    4. 只有知识库、对话历史两者完全没有相关信息，才说“这个问题我暂时不太清楚”；禁止输出“知识库未找到内容”这类话术。
    """
        resp = self.memory.stream({"input": prompt},
                                  config={"configurable": {"session_id": config.LLM_SESSION_ID}})

        return resp

    def clear_history(self):
        self.chat_history.clear()
