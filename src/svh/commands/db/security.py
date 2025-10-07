import os, secrets, string, hashlib, hmac
from typing import Tuple

_ALPH = string.ascii_letters + string.digits

def gen_userid(n: int = 10) -> str:
    return "".join(secrets.choice(_ALPH) for _ in range(n))

def gen_password(n: int = 16) -> str:
    return "".join(secrets.choice(_ALPH) for _ in range(n))

def hash_password(password: str, salt: bytes | None = None) -> Tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.sha256(salt + password.encode()).hexdigest()
    return salt.hex(), digest

def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    test = hashlib.sha256(bytes.fromhex(salt_hex) + password.encode()).hexdigest()
    return hmac.compare_digest(test, hash_hex)
