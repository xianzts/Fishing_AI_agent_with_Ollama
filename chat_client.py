from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
import os

# load local model
llm = ChatOllama(model="qwen2:7b",
                 base_url="http://127.0.0.1:11434",
                 temperature=0.7  # creation[0, 1]
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
'''
RunnableWithMessageHistory(
    runnable: Runnable,
    get_session_history: Callable[[str], BaseChatMessageHistory],
    input_messages_key: str = "input",
    history_messages_key: str = "history",
    output_messages_key: Optional[str] = None,
)
'''
memory = RunnableWithMessageHistory(
    chat_chain,
    get_history,
    input_messages_key="input",
    history_messages_key="history"
)

user = "Xianzts"

DOC_FOLDER = "./docs"          # 存放你的知识库文档目录
PERSIST_DIR = "./chroma_db"    # 向量库持久化保存的本地文件夹
CHUNK_SIZE = 800               # 单块文本大小(中文汉字)
CHUNK_OVERLAP = 150             # 块重叠，防止语义被切断
TOP_K = 3                       # 检索取出最相关3个片段

embedding = OllamaEmbeddings(model="nomic-embed-text")


def load_documents(folder_path):
    docs = []
    for filename in os.listdir(folder_path):
        fp = os.path.join(folder_path, filename)
        if filename.endswith(".pdf"):
            loader = PyPDFLoader(fp, encoding="utf-8-sig")
        elif filename.endswith(".docx"):
            loader = Docx2txtLoader(fp, encoding="utf-8-sig")
        elif filename.endswith(".txt"):
            loader = TextLoader(fp, encoding="utf-8-sig")
        else:
            continue
        docs.extend(loader.load())
    return docs


# 构建或者加载向量库
if not os.path.exists(PERSIST_DIR):
    print("正在构建钓鱼知识库向量库...")
    raw_docs = load_documents(DOC_FOLDER)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。"]
    )
    split_docs = splitter.split_documents(raw_docs)
    db = Chroma.from_documents(
        documents=split_docs,
        embedding=embedding,
        persist_directory=PERSIST_DIR
    )
    print("知识库构建完成！")
else:
    print("检测到已有向量库，直接加载，如需更新文档，请删除chroma_db文件夹重新运行！")
    db = Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding)

retriever = db.as_retriever(search_kwargs={"k": TOP_K})


# 3.RAG问答函数
def rag_ask(question: str):
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
    resp = memory.stream({"input": prompt},
                                  config={"configurable": {"session_id": "session_001"}})

    return resp, related_docs


def chat_interaction():
    print("---本地钓鱼AI Agent终端交互系统（输入“exit”退出, 输入”clear“清除上下文记忆）---")
    while True:
        new_question = input("{}>".format(user))

        if new_question.lower() == 'exit':
            print("See You Next Time!")
            break

        if new_question.lower() == 'clear':
            store.pop("session_001", None)
            print("已清空上下文记忆！")
            continue

        print("AI>", end="", flush=True)
        try:
            # stream output with each line
            ans, sources = rag_ask(new_question)
            for answer_line in ans:
                content = answer_line.content
                print(content, end="", flush=True)

            print("\n---------------")
            print("agent已生成完毕！")
            print("---------------")

        except Exception as err:
            print("\n执行异常，异常原因：{}".format(err))


if __name__ == "__main__":
    chat_interaction()