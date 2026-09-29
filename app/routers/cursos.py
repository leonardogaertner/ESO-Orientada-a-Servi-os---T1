from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common import bloqueio_exclusao, buscar_ou_404, existe, ordenar
from ..database import get_db
from ..deps import CATALOGO, EQUIPE, ESCRITA
from ..models import Aluno, Curso, Disciplina
from ..schemas import AlunoOut, CursoIn, CursoOut, DisciplinaListada

router = APIRouter(prefix="/cursos", tags=["Cursos"])
MSG_404 = "Curso não encontrado."


@router.get("", response_model=list[CursoOut], dependencies=[Depends(CATALOGO)], summary="Listar cursos")
def listar(nome: str | None = None, sort: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Curso)
    if nome:
        stmt = stmt.where(Curso.nome.ilike(f"%{nome}%"))
    stmt = ordenar(stmt, Curso, sort, {"id", "nome", "duracao_semestres", "turno"})
    return db.scalars(stmt).all()


@router.post("", response_model=CursoOut, status_code=201, dependencies=[Depends(ESCRITA)], summary="Criar curso")
def criar(dados: CursoIn, db: Session = Depends(get_db)):
    curso = Curso(**dados.model_dump())
    db.add(curso)
    db.commit()
    return curso


@router.get("/{curso_id}", response_model=CursoOut, dependencies=[Depends(CATALOGO)], summary="Buscar curso por id")
def buscar(curso_id: int, db: Session = Depends(get_db)):
    return buscar_ou_404(db, Curso, curso_id, MSG_404)


@router.put("/{curso_id}", response_model=CursoOut, dependencies=[Depends(ESCRITA)], summary="Atualizar curso")
def atualizar(curso_id: int, dados: CursoIn, db: Session = Depends(get_db)):
    curso = buscar_ou_404(db, Curso, curso_id, MSG_404)
    for campo, valor in dados.model_dump().items():
        setattr(curso, campo, valor)
    db.commit()
    return curso


@router.delete("/{curso_id}", status_code=204, dependencies=[Depends(ESCRITA)], summary="Remover curso")
def remover(curso_id: int, db: Session = Depends(get_db)):
    curso = buscar_ou_404(db, Curso, curso_id, MSG_404)
    if existe(db, Aluno.curso_id == curso_id) or existe(db, Disciplina.curso_id == curso_id):
        raise bloqueio_exclusao("O curso possui alunos ou disciplinas vinculados e não pode ser removido.")
    db.delete(curso)
    db.commit()
    return Response(status_code=204)


# ---------- relacionamentos ----------
@router.get("/{curso_id}/alunos", response_model=list[AlunoOut], dependencies=[Depends(EQUIPE)],
            summary="Listar os alunos de um curso")
def alunos_do_curso(curso_id: int, db: Session = Depends(get_db)):
    buscar_ou_404(db, Curso, curso_id, MSG_404)
    return db.scalars(select(Aluno).where(Aluno.curso_id == curso_id).order_by(Aluno.nome)).all()


@router.get("/{curso_id}/disciplinas", response_model=list[DisciplinaListada], dependencies=[Depends(CATALOGO)],
            summary="Listar as disciplinas de um curso")
def disciplinas_do_curso(curso_id: int, db: Session = Depends(get_db)):
    buscar_ou_404(db, Curso, curso_id, MSG_404)
    return db.scalars(
        select(Disciplina).where(Disciplina.curso_id == curso_id).order_by(Disciplina.semestre, Disciplina.nome)
    ).all()
