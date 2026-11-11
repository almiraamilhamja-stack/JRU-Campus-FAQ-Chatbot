"""Demo authentication for the academic prototype.

These are clearly labelled test accounts. They are NOT connected to JRU's student information system.
Only PBKDF2-HMAC-SHA256 hashes (with per-user salts) are stored in the code, never the passwords.
The demo passwords are listed in README.md so the prototype can be tested.
"""
import hashlib
import hmac
import time

PBKDF2_ITERATIONS = 200_000
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 60

# user id -> profile and password hash
DEMO_USERS = {
    "2024-00001": {
        "name": "Demo Student", "role": "Student",
        "salt": "daf0b46ffbde174319666d056274d288",
        "hash": "90366af9248d95384beed19f630009e3a173480c5398c2e65ad073574f000576",
    },
    "E-0001": {
        "name": "Demo Employee", "role": "Employee",
        "salt": "073998d012f1a1115ea06f4e2feb6837",
        "hash": "a9c6c5162937897c37aed6349da07f0d421f68e146aa06f0c106aa60d72bbdef",
    },
}


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex),
                               PBKDF2_ITERATIONS).hex()


def verify_credentials(user_id: str, password: str):
    """Return the user profile (without the hash) when the credentials are valid, otherwise None."""
    user_id = (user_id or "").strip()
    user = DEMO_USERS.get(user_id)
    # Always compute a hash so the response time does not reveal whether the id exists.
    salt = user["salt"] if user else "00" * 16
    candidate = hash_password(password or "", salt)
    expected = user["hash"] if user else "0" * 64
    if user and hmac.compare_digest(candidate, expected):
        return {"id": user_id, "name": user["name"], "role": user["role"]}
    return None


def lockout_remaining(failed_attempts: int, last_failure_ts: float, now: float = None) -> int:
    """Seconds left on a temporary lock-out after too many failed attempts (0 when not locked)."""
    now = time.time() if now is None else now
    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        return max(0, int(LOCKOUT_SECONDS - (now - last_failure_ts)))
    return 0
