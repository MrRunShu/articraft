import hashlib
from app.config import settings


def encrypt_password(password: str) -> str:
    salted = password + settings.password_salt
    return hashlib.md5(salted.encode()).hexdigest()


def verify_password(plain_password: str, encrypted_password: str) -> bool:
    return encrypt_password(plain_password) == encrypted_password
