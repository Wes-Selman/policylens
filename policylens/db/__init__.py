import os
from typing import Optional
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()

_pool: Optional[ConnectionPool] = None

def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(os.environ["POSTGRES_DSN"])
    return _pool