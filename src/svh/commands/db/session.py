from __future__ import annotations
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from svh.commands.db.config.template import load_db_template
from .models import Base

_engine = None
_Session = None

def configure_engine():
    global _engine, _Session
    url = load_db_template().get("url", "sqlite:///./hive.sqlite")
    _engine = create_engine(url, future=True, pool_pre_ping=True)
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
