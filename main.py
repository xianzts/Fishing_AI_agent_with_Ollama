from rag_services import RagServices
from llm_services import LLMServices
from user_account import UserAccount
from terminal_interaction import chat_interaction

if __name__ == "__main__":
    RAG_instance = RagServices()
    LLM_instance = LLMServices()
    account_instance = UserAccount()
    chat_interaction(RAG_instance, LLM_instance, account_instance)