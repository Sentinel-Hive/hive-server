from __future__ import annotations
import os, secrets, string, hashlib, hmac
from typing import Tuple
from pathlib import Path


_sysrand = secrets.SystemRandom()

# --------- wordlist loading -------------------------------------------------
def _load_words() -> list[str]:
    """Load words from wordlist.txt (one per line). Falls back to a small set."""
    p = Path(__file__).with_name("wordlist.txt")
    if p.exists():
        words = [w.strip().lower() for w in p.read_text(encoding="utf-8").splitlines()
                 if w.strip() and not w.startswith("#")]
        # basic hygiene: only simple ascii words
        words = [w for w in words if w.isascii() and w.replace("-", "").isalpha()]
        if len(words) >= 1024:
            return words
    # Tiny fallback (dev only). For real strength, add a 2k+ word list to wordlist.txt
    return [
        "sky","river","stone","forest","coffee","apple","delta","ember","nova","pilot",
        "solar","ocean","pixel","orbit","rocket","silver","amber","hazel","neon","quartz",
        "tiger","otter","panda","falcon","lynx","eagle","zephyr","cobalt","crimson","violet"
    ]

_WORDS = None
def _words() -> list[str]:
    global _WORDS
    if _WORDS is None:
        _WORDS = _load_words()
    return _WORDS

# --------- memorable generators --------------------------------------------
def _mem_username(words:int=2, sep:str="-", digits:int=2) -> str:
    pool = _words()
    parts = [_sysrand.choice(pool) for _ in range(max(1, words))]
    suffix = "".join(_sysrand.choice(string.digits) for _ in range(max(0, digits)))
    return sep.join(parts) + (suffix if suffix else "")

def _mem_passphrase(words:int=4, sep:str="-", add_digit:bool=True, add_symbol:bool=True, cap_first:bool=False) -> str:
    pool = _words()
    parts = [_sysrand.choice(pool) for _ in range(max(3, words))]  # ≥3 words minimum
    if cap_first and parts:
        parts[0] = parts[0].capitalize()
    pw = sep.join(parts)
    if add_digit:
        pw += str(_sysrand.randrange(10, 100))  # 2 digits
    if add_symbol:
        pw += _sysrand.choice("!@#$%^&*")
    return pw

# --------- env-configurable front doors (used by the rest of the code) -----
def gen_userid() -> str:
    """
    Generate a human-friendly user_id.
    Config (env):
      SVH_USER_WORDS   (default 2)
      SVH_USER_SEP     (default '-')
      SVH_USER_DIGITS  (default 2)
      SVH_CRED_STYLE   ('memorable' or 'random'; default 'memorable')
    """
    style = os.getenv("SVH_CRED_STYLE", "memorable").lower()
    if style == "random":
        # old behavior: 10 random URL-safe chars
        return secrets.token_urlsafe(8).rstrip("=")
    return _mem_username(
        words=int(os.getenv("SVH_USER_WORDS", "2")),
        sep=os.getenv("SVH_USER_SEP", "-"),
        digits=int(os.getenv("SVH_USER_DIGITS", "2")),
    )

def gen_password() -> str:
    """
    Generate a human-friendly password/passphrase.
    Config (env):
      SVH_PASS_WORDS   (default 4)
      SVH_PASS_SEP     (default '-')
      SVH_PASS_DIGIT   (default '1' → add digits)
      SVH_PASS_SYMBOL  (default '1' → add symbol)
      SVH_PASS_CAP     (default '0' → capitalize first word)
      SVH_CRED_STYLE   ('memorable' or 'random'; default 'memorable')
    """
    style = os.getenv("SVH_CRED_STYLE", "memorable").lower()
    if style == "random":
        # old behavior: 16 random chars (url-safe)
        return secrets.token_urlsafe(12).rstrip("=")
    return _mem_passphrase(
        words=int(os.getenv("SVH_PASS_WORDS", "4")),
        sep=os.getenv("SVH_PASS_SEP", "-"),
        add_digit=os.getenv("SVH_PASS_DIGIT", "1") not in ("0", "false", "no"),
        add_symbol=os.getenv("SVH_PASS_SYMBOL", "1") not in ("0", "false", "no"),
        cap_first=os.getenv("SVH_PASS_CAP", "0") in ("1", "true", "yes"),
    )

def hash_password(password: str, salt: bytes | None = None) -> Tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.sha256(salt + password.encode()).hexdigest()
    return salt.hex(), digest

def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    test = hashlib.sha256(bytes.fromhex(salt_hex) + password.encode()).hexdigest()
    return hmac.compare_digest(test, hash_hex)
