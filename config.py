import os
from dotenv import load_dotenv

AGENT_MODEL = "qwen2:7b"
EMBEDDING_MODEL = "nomic-embed-text"
URL = "http://127.0.0.1:11434"
TEMP = 0.7
DOC_FOLDER = "./docs"          # 存放你的知识库文档目录
PERSIST_DIR = "./chroma_db"    # 向量库持久化保存的本地文件夹
CHUNK_SIZE = 300               # 单块文本大小(中文汉字)
CHUNK_OVERLAP = 120             # 块重叠，防止语义被切断
TOP_K = 3                       # 检索取出最相关3个片段
THRESHOLD = 0.7                 # 相似度阈值
SEARCH_TYPE = "similarity"      # 检索方式

SECRET_KEY_LENGTH = 48

SYSTEM_PROMPT = "你是专业技术助手，回答简洁清晰。"
LLM_SESSION_ID = "session_001"

# 读取env配置
load_dotenv()

# 加载JWT配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES"))

# 数据库配置
DB = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB"),
    "charset": "utf8mb4"
}