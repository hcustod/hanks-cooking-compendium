import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.engine import Engine

metadata = MetaData()

def get_database_url() -> str:
    url = os.geteng("DATABASE_URL")
    if not url: 
        raise RuntimeError("Database url is not set.")
    return url 

def get_engine() -> Engine:
    return create_engine(get_database_url(), future=True)