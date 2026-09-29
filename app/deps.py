import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .enums import Perfil
from .errors import AppError
from .models import TokenRevogado, Usuario
from .security import decodificar_token

bearer = HTTPBearer(auto_error=False, description="Cole o token obtido em POST /auth/login")


def _nao_autenticado() -> AppError:
    return AppError(401, "TOKEN_INVALIDO", "Autenticação necessária ou token expirado.")


def payload_atual(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict:
    if cred is None:
        raise _nao_autenticado()
    try:
        payload = decodificar_token(cred.credentials)
    except jwt.PyJWTError:
        raise _nao_autenticado()
    if db.get(TokenRevogado, payload["jti"]) is not None:
        raise _nao_autenticado()
    return payload


def usuario_atual(payload: dict = Depends(payload_atual), db: Session = Depends(get_db)) -> Usuario:
    try:
        usuario = db.get(Usuario, int(payload["sub"]))
    except ValueError:
        usuario = None
    if usuario is None or not usuario.ativo:
        raise _nao_autenticado()
    return usuario


def exige(*perfis: Perfil):
    """Dependência que só libera os perfis informados (ADMIN sempre tem acesso)."""
    permitidos = {p.value for p in perfis} | {Perfil.ADMIN.value}

    def verificar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.perfil not in permitidos:
            raise AppError(403, "ACESSO_NEGADO", "Você não tem permissão para esta operação.")
        return usuario

    return verificar


def exige_proprio_aluno(usuario: Usuario, aluno_id: int) -> None:
    """Um usuário ALUNO só acessa os próprios dados."""
    if usuario.perfil == Perfil.ALUNO.value and usuario.aluno_id != aluno_id:
        raise AppError(403, "ACESSO_NEGADO", "Você só pode acessar os seus próprios dados.")


# Atalhos de permissão usados nos routers
ESCRITA = exige(Perfil.SECRETARIA)                                        # CRUD administrativo
EQUIPE = exige(Perfil.SECRETARIA, Perfil.PROFESSOR)                       # leitura da equipe
CATALOGO = exige(Perfil.SECRETARIA, Perfil.PROFESSOR, Perfil.ALUNO)       # leitura aberta a todos os perfis
