import os 
from sqlalchemy import create_engine

_engine = None

def get_engine():
    global _engine
    if _engine is None: 
        url = os.getenv(
            "DATABASE_URL", 
            "postgresql+psycopg2://postgres:postgres@localhost:5432/hcc_db"
        )
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


