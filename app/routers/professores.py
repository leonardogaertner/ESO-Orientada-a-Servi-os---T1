from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..common import bloqueio_exclusao, buscar_ou_404, existe, garantir_unico, ordenar
from ..database import get_db
from ..deps import EQUIPE, ESCRITA
from ..enums import Titulacao
from ..models import Disciplina, Professor, Usuario
from ..schemas import DisciplinaListada, ProfessorIn, ProfessorOut

router = APIRouter(prefix="/professores", tags=["Professores"])
MSG_404 = "Professor não encontrado."


def _checar_unicos(db: Session, dados: ProfessorIn, ignorar_id: int | None = None):
    garantir_unico(db, Professor, "cpf", dados.cpf, "CPF_JA_CADASTRADO", "Já existe um professor com este CPF.", ignorar_id)
    garantir_unico(db, Professor, "email", dados.email, "EMAIL_JA_CADASTRADO", "Já existe um professor com este e-mail.", ignorar_id)


@router.get("", response_model=list[ProfessorOut], dependencies=[Depends(EQUIPE)], summary="Listar professores")
def listar(
    nome: str | None = None,
    titulacao: Titulacao | None = None,
    sort: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Professor)
    if nome:
        stmt = stmt.where(Professor.nome.ilike(f"%{nome}%"))
    if titulacao:
        stmt = stmt.where(Professor.titulacao == titulacao.value)
    stmt = ordenar(stmt, Professor, sort, {"id", "nome", "email", "titulacao"})
    return db.scalars(stmt).all()


@router.post("", response_model=ProfessorOut, status_code=201, dependencies=[Depends(ESCRITA)],
             summary="Cadastrar professor")
def criar(dados: ProfessorIn, db: Session = Depends(get_db)):
    _checar_unicos(db, dados)
    professor = Professor(**dados.model_dump())
    db.add(professor)
    db.commit()
    return professor


@router.get("/{professor_id}", response_model=ProfessorOut, dependencies=[Depends(EQUIPE)],
            summary="Buscar professor por id")
def buscar(professor_id: int, db: Session = Depends(get_db)):
    return buscar_ou_404(db, Professor, professor_id, MSG_404)


@router.put("/{professor_id}", response_model=ProfessorOut, dependencies=[Depends(ESCRITA)],
            summary="Atualizar professor")
def atualizar(professor_id: int, dados: ProfessorIn, db: Session = Depends(get_db)):
    professor = buscar_ou_404(db, Professor, professor_id, MSG_404)
    _checar_unicos(db, dados, ignorar_id=professor_id)
    for campo, valor in dados.model_dump().items():
        setattr(professor, campo, valor)
    db.commit()
    return professor


@router.delete("/{professor_id}", status_code=204, dependencies=[Depends(ESCRITA)], summary="Remover professor")
def remover(professor_id: int, db: Session = Depends(get_db)):
    professor = buscar_ou_404(db, Professor, professor_id, MSG_404)
    if existe(db, Disciplina.professor_id == professor_id):
        raise bloqueio_exclusao("O professor ainda ministra disciplinas e não pode ser removido.")
    db.execute(delete(Usuario).where(Usuario.professor_id == professor_id))  # remove também o login vinculado
    db.delete(professor)
    db.commit()
    return Response(status_code=204)


# ---------- relacionamento ----------
@router.get("/{professor_id}/disciplinas", response_model=list[DisciplinaListada], dependencies=[Depends(EQUIPE)],
            summary="Listar as disciplinas de um professor")
def disciplinas_do_professor(professor_id: int, db: Session = Depends(get_db)):
    buscar_ou_404(db, Professor, professor_id, MSG_404)
    return db.scalars(
        select(Disciplina).where(Disciplina.professor_id == professor_id).order_by(Disciplina.nome)
    ).all()
