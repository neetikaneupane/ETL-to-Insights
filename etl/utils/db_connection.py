import os
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")
ENV_PATH = os.path.join(BASE_DIR, "config", ".env")

load_dotenv(ENV_PATH)


def load_config():
    with open(CONFIG_PATH, "r") as f:
        raw_text = f.read()
    expanded_text = os.path.expandvars(raw_text)
    config = yaml.safe_load(expanded_text)
    return config


_engine = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    config = load_config()
    db = config["database"]

    connection_url = (
        f"postgresql+psycopg2://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['name']}"
    )

    _engine = create_engine(connection_url, pool_pre_ping=True)
    return _engine