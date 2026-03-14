
from sqlalchemy import create_engine, text, Engine
from define import BASE_URL, HTTP_TIMEOUT, DB_PATH

_g_engine: Engine = None
def getEngine()->Engine:
    global _g_engine
    if not _g_engine:
        _g_engine = create_engine(f"sqlite:///{DB_PATH}")
    return _g_engine