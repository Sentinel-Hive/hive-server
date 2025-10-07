from contextlib import contextmanager
from ...db.session import session_scope, create_all

@contextmanager
def get_session():
    create_all()  # idempotent; ensures tables exist
    with session_scope() as s:
        yield s
