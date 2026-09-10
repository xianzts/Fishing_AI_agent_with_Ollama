from src import RagServices
import logging

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    RagInstance = RagServices()
    RagInstance.load_public_vector_dataset()
