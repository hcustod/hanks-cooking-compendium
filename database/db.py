import os 
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

_engine = None

def get_engine():
    global _engine
    if _engine is None: 
        url = URL.create(
            drivername="postgresql+psycopg",
            username=os.getenv("POSTGRES_USER", "hcc"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST", "db"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "hcc"),
        )
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


