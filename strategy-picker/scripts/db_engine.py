
import sqlcipher3
from sqlalchemy import create_engine, event, Engine
from define import BASE_URL, HTTP_TIMEOUT, DB_PATH

import os
_g_engine: Engine = None

def getEngine() -> Engine:
    global _g_engine
    if not _g_engine:
        def _creator():
            conn = sqlcipher3.connect(DB_PATH)
            conn.execute(f"PRAGMA key='{os.environ.get("DB_KEY", "stock2026")}'")
            return conn

        _g_engine = create_engine("sqlite+pysqlite://", creator=_creator)
    return _g_engine