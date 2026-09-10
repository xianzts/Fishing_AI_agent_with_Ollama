from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_classic.retrievers import EnsembleRetriever

import os
import logging

from src.core import config
from src.db.db_services import DBServices

logger = logging.getLogger(__name__)  # 使用当前模块名创建 logger


class RagServices:
    def __init__(self, log_callback=None):
        self.embedding = OllamaEmbeddings(model=config.EMBEDDING_MODEL)

        # 缓存retriever
        self.public_retriever = None
        self.private_retrievers = {}
        self.combined_retrievers = {}

        # log_callback: 传入一个日志回调函数
        self.log = log_callback or logger.info

    def load_documents(self, folder_path):
        docs = []
        for filename in os.listdir(folder_path):
            fp = os.path.join(folder_path, filename)
            try:
                if filename.endswith(".pdf"):
                    loader = PyPDFLoader(fp)
                elif filename.endswith(".docx"):
                    loader = Docx2txtLoader(fp)
                elif filename.endswith(".txt"):
                    loader = TextLoader(fp, encoding="utf-8-sig")
                else:
                    continue

                loaded = loader.load()
                # 把文件名写进 metadata，用于后续按文件删除
                for doc in loaded:
                    doc.metadata["source"] = filename

                docs.extend(loaded)
                self.log(f"成功加载文档: {filename}")

            except Exception as e:
                self.log(f"加载文件失败: {filename}, 错误: {e}")
        return docs

    def load_public_vector_dataset(self):
        collection_name = config.PUBLIC_COLLECTION_NAME  # 例如 "public_knowledge"

        # 1. 统一使用统一的持久化目录，通过 collection_name 隔离公有库
        db = Chroma(
            persist_directory=config.PERSIST_DIR,
            embedding_function=self.embedding,
            collection_name=collection_name
        )

        # 2. 判断公有库是否为空（而不是判断目录是否存在）
        if db._collection.count() == 0:
            self.log("检测到公共知识库为空，正在构建钓鱼公共知识库向量库...")

            # 加载并切分文档
            raw_docs = self.load_documents(config.DOC_FOLDER)
            if not raw_docs:
                self.log("警告：未找到任何公共文档，跳过构建")
                return None

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
            )
            split_docs = splitter.split_documents(raw_docs)

            # 3. 构建并持久化（覆盖当前的空 db）
            db = Chroma.from_documents(
                documents=split_docs,
                embedding=self.embedding,
                persist_directory=config.PERSIST_DIR,
                collection_name=collection_name
            )
            self.log("公共知识库构建完成！")
        else:
            self.log("检测到已有公共知识库，直接加载。如需更新文档，请清空该 collection 后重新运行！")

        # 4. 生成检索器
        retriever = db.as_retriever(
            search_type=config.SEARCH_TYPE,
            score_threshold=config.THRESHOLD,
            search_kwargs={"k": config.TOP_K}
        )
        return retriever

    def load_private_vector_dataset(self, user_id):
        collection_name = f"{config.USER_PREFIX}{user_id}"

        self.log(f"正在加载用户 {user_id} 的私有知识库...")
        try:
            # 1. 始终使用统一的持久化目录 config.PERSIST_DIR
            # 2. 通过 collection_name 指定加载哪个用户的库
            db = Chroma(
                persist_directory=config.PERSIST_DIR,  # 统一目录
                embedding_function=self.embedding,  # 统一的 Embedding 模型
                collection_name=collection_name  # 区分用户
            )

            # 3. 判断该用户的 collection 是否有数据
            # 直接查数量，如果为0说明还没上传过私有知识
            if db._collection.count() == 0:
                self.log(f"用户 {user_id} 的私有知识库为空")
                return None

            # 4. 生成检索器
            retriever = db.as_retriever(
                search_type=config.SEARCH_TYPE,
                score_threshold=config.THRESHOLD,
                search_kwargs={"k": config.TOP_K}
            )
            return retriever

        except Exception as e:
            # 如果 collection 不存在，Chroma 可能会报错，这里捕获一下
            self.log(f"加载用户 {user_id} 私有知识库失败: {e}")
            return None

    # 添加用户个人私有知识库
    def add_private_document(self, user_id, folder_path):
        """
        将一个文件夹下的所有文档加入指定用户的私有知识库。
        - 支持 PDF / DOCX / TXT
        - 若该用户 collection 不存在，会自动创建
        - 已存在则追加，不覆盖历史数据
        """
        # 1. 加载文件夹下所有文档
        raw_docs = self.load_documents(folder_path)
        if not raw_docs:
            self.log(f"用户 {user_id} 上传的文件夹中未解析出任何文档")
            return False, "未解析出任何文档", 0

        # 2. 切分
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
        split_docs = splitter.split_documents(raw_docs)

        # 3. 补充 metadata：标记归属用户（source 已在 load_documents 中写入）
        for doc in split_docs:
            doc.metadata["user_id"] = user_id

        # 4. 追加写入用户的 collection
        try:
            collection_name = f"{config.USER_PREFIX}{user_id}"
            vector_store = Chroma(
                persist_directory=config.PERSIST_DIR,
                embedding_function=self.embedding,
                collection_name=collection_name
            )
            vector_store.add_documents(split_docs)
            self.log(f"用户 {user_id} 私有文档已追加，共 {len(split_docs)} 个 chunk")
            return True, "上传成功", len(split_docs)

        except Exception as e:
            self.log(f"写入向量库失败: {e}")
            return False, f"写入向量库失败: {e}", 0

    def get_public_retriever(self):
        if self.public_retriever is None:
            self.public_retriever = self.load_public_vector_dataset()
        self.log("加载用户公有向量库成功")
        return self.public_retriever

    def get_private_retriever(self, user_id):
        """获取指定用户的私有库检索器（按需加载，带内存缓存）"""
        if user_id not in self.private_retrievers:
            self.private_retrievers[user_id] = self.load_private_vector_dataset(user_id)
        self.log("加载用户私有向量库成功")
        return self.private_retrievers[user_id]

    def get_combined_retriever(self, user_id):
        if user_id in self.combined_retrievers:
            self.log("从内存缓存中加载知识库")
            return self.combined_retrievers[user_id]

        public_retriever = self.get_public_retriever()
        private_retriever = self.get_private_retriever(user_id)

        if private_retriever is None:
            # 用户还没有私有知识，只用公有库
            self.log("用户还没有私有知识，只用公有库")
            self.combined_retrievers[user_id] = public_retriever
            return public_retriever

        # 用 EnsembleRetriever 融合两个库
        self.log("正在合并公有知识库和个人私有知识库")
        ensemble = EnsembleRetriever(
            retrievers=[private_retriever, public_retriever],
            weights=[0.7, 0.3]  # 私有库权重更高
        )

        self.combined_retrievers[user_id] = ensemble
        self.log("知识库合并成功")
        return ensemble
