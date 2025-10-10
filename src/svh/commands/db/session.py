from __future__ import annotations
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from svh.commands.db.config.template import load_db_template
from .models import Base
from svh.commands.server.util_config import get_database_url
DB_URL = get_database_url()
_engine = None
_Session = None

def configure_engine():
    global _engine, _Session
    _engine = create_engine(DB_URL, future=True, pool_pre_ping=True)
    _Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

def create_all():
    if _engine is None:
        configure_engine()
    Base.metadata.create_all(_engine)

@contextmanager
def session_scope():
    if _Session is None:
        configure_engine()
    s = _Session()
    try:
        yield s
        s.commit()
    except:
        s.rollback()
        raise
    finally:
        s.close()

def get_engine():
    if _engine is None:
        configure_engine()
    return _engine
