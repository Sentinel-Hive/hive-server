import os, time, hmac, hashlib, threading
from typing import Optional, Tuple

_SECRET = os.environ.get("SVH_AUTH_SECRET", "dev-change-me")

class _Cache:
    def __init__(self):
        self._d = {}; self._lock = threading.Lock()
    def set(self, k: str, v: str, ttl: int):
        with self._lock: self._d[k] = (v, time.time() + ttl)
    def get(self, k: str) -> Optional[str]:
        with self._lock:
            item = self._d.get(k)
            if not item: return None
            val, exp = item
            if exp < time.time():
                del self._d[k]; return None
            return val
    def delete(self, k: str):
        with self._lock: self._d.pop(k, None)

cache = _Cache()

def make_token(user_id: str, ts: Optional[int] = None) -> str:
    ts = ts or int(time.time())
    msg = f"{user_id}:{ts}".encode()
    sig = hmac.new(_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return f"{user_id}.{ts}.{sig}"

def parse_token(token: str) -> Optional[Tuple[str,int,str]]:
    try:
        u, t, s = token.split("."); return (u, int(t), s)
    except Exception:
        return None
