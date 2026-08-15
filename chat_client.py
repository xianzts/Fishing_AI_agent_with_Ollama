from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

# load local model
llm = ChatOllama(model="qwen2:7b",
                base_url="http://127.0.0.1:11434",
                temperature=0.7   # creation[0, 1]
                )

# 对话prompt模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是专业技术助手，回答简洁清晰。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

store = {}


def get_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


# 组装对话链
chat_chain = prompt | llm

# 上下文记忆
memory = RunnableWithMessageHistory(
    chat_chain,
    get_history,
    input_messages_key="input",
    history_messages_key="history"
)

user = "Xianzts"


def chat_interaction():
    print("---本地钓鱼AI Agent终端交互系统（输入“exit”退出）---")
    while True:
        new_question = input("{}>".format(user))

        if new_question.lower() == 'exit':
            print("See You Next Time!")
            break

        print("AI>", end="", flush=True)
        try:
            # output with each line
            for answer_line in memory.stream({"input": new_question}, config={"configurable": {"session_id": "session_001"}}):
                content = answer_line.content
                print(content, end="", flush=True)

            print("\n---------------")
            print("agent已生成完毕！")
            print("---------------")

        except Exception as err:
            print("\n执行异常，异常原因：{}".format(err))


if __name__ == "__main__":
    chat_interaction()