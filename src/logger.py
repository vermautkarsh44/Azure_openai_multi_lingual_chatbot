import os
import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    log_file = "logs/log.txt"
    file_handler = logging.FileHandler(log_file)

    logger = logging.getLogger(__name__)
    logger.addHandler(file_handler)

    return logger