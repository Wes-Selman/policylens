import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool
        _pool = ConnectionPool(os.environ["POSTGRES_DSN"])
    return _pool
