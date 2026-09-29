from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import payload_atual, usuario_atual
from ..errors import AppError
from ..models import TokenRevogado, Usuario
from ..schemas import LoginIn, LoginOut, MeOut
from ..security import criar_token, verificar_senha

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=LoginOut, summary="Autenticar e obter token")
def login(dados: LoginIn, db: Session = Depends(get_db)):
    usuario = db.scalar(select(Usuario).where(Usuario.email == dados.email.lower()))
    if usuario is None or not usuario.ativo or not verificar_senha(dados.senha, usuario.senha_hash):
        raise AppError(401, "CREDENCIAIS_INVALIDAS", "E-mail ou senha incorretos.")
    token, expira_em = criar_token(usuario.id, usuario.perfil)
    return {"token": token, "tipo": "Bearer", "expira_em": expira_em, "perfil": usuario.perfil}


@router.get("/me", response_model=MeOut, summary="Dados do usuário autenticado")
def me(usuario: Usuario = Depends(usuario_atual)):
    return usuario


@router.post("/logout", status_code=204, summary="Invalidar o token atual")
def logout(payload: dict = Depends(payload_atual), db: Session = Depends(get_db)):
    agora = datetime.now(timezone.utc).replace(tzinfo=None)
    db.execute(delete(TokenRevogado).where(TokenRevogado.expira_em < agora))  # limpeza de tokens já expirados
    expira = datetime.fromtimestamp(payload["exp"], timezone.utc).replace(tzinfo=None)
    db.merge(TokenRevogado(jti=payload["jti"], expira_em=expira))
    db.commit()
    return Response(status_code=204)
