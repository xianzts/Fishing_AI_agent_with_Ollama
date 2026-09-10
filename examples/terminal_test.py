from src import RagServices
from src import LLMServices
from src import UserAccount
from terminal_interaction import chat_interaction

import logging


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    RAG_instance = RagServices()
    LLM_instance = LLMServices()
    account_instance = UserAccount()
    chat_interaction(RAG_instance, LLM_instance, account_instance)