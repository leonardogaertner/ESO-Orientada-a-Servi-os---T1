import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from .config import ALGORITHM, SECRET_KEY, TOKEN_EXPIRE_SECONDS

_ITERACOES = 210_000


def hash_senha(senha: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, _ITERACOES)
    return f"pbkdf2_sha256${_ITERACOES}${salt.hex()}${dk.hex()}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    try:
        _, iteracoes, salt, esperado = armazenado.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), int(iteracoes))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), esperado)


def criar_token(usuario_id: int, perfil: str) -> tuple[str, int]:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "perfil": perfil,
        "jti": uuid.uuid4().hex,
        "iat": agora,
        "exp": agora + timedelta(seconds=TOKEN_EXPIRE_SECONDS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), TOKEN_EXPIRE_SECONDS


def decodificar_token(token: str) -> dict:
    """Levanta jwt.PyJWTError se o token for inválido ou estiver expirado."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp", "jti", "sub"]})
