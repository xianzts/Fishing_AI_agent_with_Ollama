from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

import os

import config


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


class RagServices:
    def __init__(self, log_callback=None):
        self.embedding = OllamaEmbeddings(model=config.EMBEDDING_MODEL)
        # log_callback: 传入一个日志回调函数
        self.log = log_callback or print

    def load_vector_dataset(self):
        # 构建或者加载向量库
        if not os.path.exists(config.PERSIST_DIR):
            self.log("正在构建钓鱼知识库向量库...")
            raw_docs = load_documents(config.DOC_FOLDER)
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                separators=["\n\n", "\n", "。", "，"]
            )
            split_docs = splitter.split_documents(raw_docs)
            db = Chroma.from_documents(
                documents=split_docs,
                embedding=self.embedding,
                persist_directory=config.PERSIST_DIR
            )
            self.log("知识库构建完成！")
        else:
            self.log("检测到已有向量库，直接加载，如需更新文档，请删除chroma_db文件夹重新运行！")
            db = Chroma(persist_directory=config.PERSIST_DIR, embedding_function=self.embedding)

        retriever = db.as_retriever(
            search_kwargs={"k": config.TOP_K},
            score_threshold=config.THRESHOLD,
            search_type=config.SEARCH_TYPE
        )
        return retriever
