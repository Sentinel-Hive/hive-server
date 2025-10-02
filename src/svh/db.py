"""
Database initialization and management utilities.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from .db_template_utils import load_db_template, reset_db_template

DB_FILENAME = os.environ.get("SVH_DB_FILENAME", "svh.sqlite3")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", DB_FILENAME)
DB_URI = f"sqlite:///{os.path.abspath(DB_PATH)}"

def db_exists():
	"""Check if the database file exists."""
	return os.path.exists(DB_PATH)

def create_db_from_template():
	"""Create a new database using the current template."""
	template = load_db_template()
	engine = create_engine(DB_URI, echo=template.get("settings", {}).get("echo", False), future=template.get("settings", {}).get("future", True))
	Base.metadata.create_all(engine)
	return engine

def get_engine():
	"""Get a SQLAlchemy engine, creating DB if needed."""
	if not db_exists():
		print("Database not found. Initializing from template...")
		return create_db_from_template()
	return create_engine(DB_URI)

def get_session():
	"""Get a SQLAlchemy session."""
	engine = get_engine()
	Session = sessionmaker(bind=engine)
	return Session()

def reset_db_to_default():
	"""Reset the DB template to default settings."""
	reset_db_template()

def edit_db_template(edit_func):
	"""Edit the DB template using a provided function."""
	from .db_template_utils import edit_db_template as _edit
	_edit(edit_func)
