import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from datetime import datetime, timedelta
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

load_dotenv()
APP_ENV = os.getenv("APP_ENV", "development").lower()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError("Configure uma SECRET_KEY aleatória e privada em produção.")
    SECRET_KEY = "local-development-only-change-before-deploy"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # Legacy hashes are rehashed on successful login.
argon2 = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return argon2.hash(password)


def verify_and_upgrade_password(password: str, encoded: str) -> tuple[bool, str | None]:
    if encoded.startswith("$argon2"):
        try:
            return argon2.verify(encoded, password), None
        except (VerifyMismatchError, Argon2Error):
            return False, None
    try:
        valid = pwd_context.verify(password, encoded)
    except (ValueError, TypeError):
        return False, None
    return valid, hash_password(password) if valid else None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    payload.update({"exp": datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)), "type": "access"})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_signed_token(data: dict, minutes: int) -> str:
    payload = data.copy()
    payload.update({"exp": datetime.utcnow() + timedelta(minutes=minutes)})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_signed_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hmac.new(SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()


def get_fernet() -> Fernet:
    key = os.getenv("MFA_ENCRYPTION_KEY")
    if not key:
        if APP_ENV == "production":
            raise RuntimeError("Configure MFA_ENCRYPTION_KEY aleatória e privada em produção.")
        key = base64.urlsafe_b64encode(hashlib.sha256((SECRET_KEY + ":taskflow-mfa").encode()).digest()).decode()
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("MFA_ENCRYPTION_KEY deve ser uma chave Fernet válida.") from exc


def encrypt_secret(value: str) -> str:
    return get_fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(status_code=503, detail="Não foi possível abrir a chave do autenticador; confira MFA_ENCRYPTION_KEY.") from exc


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def totp_code(secret: str, for_time: int | None = None) -> str:
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
    counter = int((for_time or int(time.time())) // 30)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    number = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff) % 1_000_000
    return f"{number:06d}"


def verify_totp(secret: str, code: str) -> bool:
    if len(code) != 6 or not code.isdigit():
        return False
    now = int(time.time())
    return any(hmac.compare_digest(totp_code(secret, now + delta * 30), code) for delta in (-1, 0, 1))


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_signed_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
