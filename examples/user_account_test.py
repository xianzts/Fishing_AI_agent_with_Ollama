from src import UserAccount

import logging

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    user_account_instance = UserAccount()
    user_account_instance.register_account("Ying1", "Ying")