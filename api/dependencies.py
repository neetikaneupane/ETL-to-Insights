from etl.utils.db_connection import get_engine


def get_db():
    engine = get_engine()
    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()