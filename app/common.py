from math import ceil

from fastapi import Query
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from .errors import AppError
from .models import Matricula


def buscar_ou_404(db: Session, model, id_: int, mensagem: str):
    obj = db.get(model, id_)
    if obj is None:
        raise AppError(404, "RECURSO_NAO_ENCONTRADO", mensagem)
    return obj


def existe(db: Session, condicao) -> bool:
    return bool(db.scalar(select(exists().where(condicao))))


def garantir_unico(db: Session, model, campo: str, valor, erro: str, mensagem: str, ignorar_id: int | None = None):
    stmt = select(model.id).where(getattr(model, campo) == valor)
    if ignorar_id is not None:
        stmt = stmt.where(model.id != ignorar_id)
    if db.scalar(stmt) is not None:
        raise AppError(409, erro, mensagem)


def bloqueio_exclusao(mensagem: str) -> AppError:
    return AppError(409, "EXCLUSAO_BLOQUEADA", mensagem)


def ordenar(stmt, model, sort: str | None, permitidos: set[str]):
    """sort=nome (crescente) ou sort=-nome (decrescente)."""
    if not sort:
        return stmt.order_by(model.id)
    desc = sort.startswith("-")
    campo = sort[1:] if desc else sort
    if campo not in permitidos:
        raise AppError(
            400, "PARAMETRO_INVALIDO",
            f"Campo de ordenação inválido: '{campo}'. Permitidos: {', '.join(sorted(permitidos))}.",
        )
    coluna = getattr(model, campo)
    return stmt.order_by(coluna.desc() if desc else coluna.asc(), model.id)


class Paginacao:
    """Parâmetros de paginação: page (padrão 1) e limit (padrão 10, máximo 100)."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Número da página (começa em 1)"),
        limit: int = Query(10, ge=1, le=100, description="Itens por página (máx. 100)"),
    ):
        self.page = page
        self.limit = limit


def paginar(db: Session, stmt, p: Paginacao) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    itens = db.scalars(stmt.limit(p.limit).offset((p.page - 1) * p.limit)).all()
    return {
        "page": p.page,
        "limit": p.limit,
        "total": total,
        "total_pages": ceil(total / p.limit) if total else 0,
        "data": itens,
    }


def vagas_ocupadas(db: Session, disciplina_id: int) -> int:
    """Vagas ocupadas = matrículas em andamento (CURSANDO) na disciplina."""
    return db.scalar(
        select(func.count()).select_from(Matricula)
        .where(Matricula.disciplina_id == disciplina_id, Matricula.situacao == "CURSANDO")
    )
