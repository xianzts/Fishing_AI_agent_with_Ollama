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

    def stream_answer(self, question: str, retriever):
        # 检索知识库
        related_docs = retriever.invoke(question)
        context = "\n====\n".join([doc.page_content for doc in related_docs])

        # RAG提示词：强制模型只能使用知识库上下文，抑制幻觉
        prompt = f"""
    【知识库上下文】
    {context}

    用户问题：{question}

    请严格基于上面【知识库上下文】回答用户问题。
    如果上下文没有相关信息，请直接回答："知识库未找到该内容"，不要编造信息。
    """
        resp = self.memory.stream({"input": prompt},
                             config={"configurable": {"session_id": "session_001"}})

        return resp

    def clear_history(self):
        self.chat_history.clear()



