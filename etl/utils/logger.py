import logging
import os
from etl.utils.db_connection import load_config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_logger(name):
    config = load_config()
    log_config = config["logging"]

    log_dir = os.path.join(BASE_DIR, log_config["log_dir"])
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, log_config["log_file"])
    log_level = getattr(logging, log_config["level"].upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger