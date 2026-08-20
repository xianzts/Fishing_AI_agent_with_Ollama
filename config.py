AGENT_MODEL = "qwen2:7b"
EMBEDDING_MODEL = "nomic-embed-text"
URL = "http://127.0.0.1:11434"
TEMP = 0.7
DOC_FOLDER = "./docs"          # 存放你的知识库文档目录
PERSIST_DIR = "./chroma_db"    # 向量库持久化保存的本地文件夹
CHUNK_SIZE = 800               # 单块文本大小(中文汉字)
CHUNK_OVERLAP = 150             # 块重叠，防止语义被切断
TOP_K = 3                       # 检索取出最相关3个片段

SYSTEM_PROMPT = "你是专业技术助手，回答简洁清晰。"

USER = "Xianzts"