from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common import (Paginacao, bloqueio_exclusao, buscar_ou_404, existe, garantir_unico, ordenar, paginar,
                      vagas_ocupadas)
from ..database import get_db
from ..deps import CATALOGO, EQUIPE, ESCRITA
from ..errors import AppError
from ..models import Curso, Disciplina, Matricula, Professor
from ..schemas import DisciplinaDetalhe, DisciplinaIn, DisciplinaOut, MatriculaDaDisciplina, Pagina

router = APIRouter(prefix="/disciplinas", tags=["Disciplinas"])
MSG_404 = "Disciplina não encontrada."


def _validar_referencias(db: Session, dados: DisciplinaIn):
    buscar_ou_404(db, Curso, dados.curso_id, "Curso não encontrado.")
    buscar_ou_404(db, Professor, dados.professor_id, "Professor não encontrado.")


@router.get("", response_model=Pagina[DisciplinaOut], dependencies=[Depends(CATALOGO)],
            summary="Listar disciplinas (filtros e paginação)")
def listar(
    nome: str | None = None,
    curso_id: int | None = None,
    semestre: int | None = None,
    professor_id: int | None = None,
    sort: str | None = None,
    p: Paginacao = Depends(),
    db: Session = Depends(get_db),
):
    stmt = select(Disciplina)
    if nome:
        stmt = stmt.where(Disciplina.nome.ilike(f"%{nome}%"))
    if curso_id is not None:
        stmt = stmt.where(Disciplina.curso_id == curso_id)
    if semestre is not None:
        stmt = stmt.where(Disciplina.semestre == semestre)
    if professor_id is not None:
        stmt = stmt.where(Disciplina.professor_id == professor_id)
    stmt = ordenar(stmt, Disciplina, sort, {"id", "codigo", "nome", "semestre", "carga_horaria"})
    return paginar(db, stmt, p)


@router.post("", response_model=DisciplinaOut, status_code=201, dependencies=[Depends(ESCRITA)],
             summary="Criar disciplina")
def criar(dados: DisciplinaIn, db: Session = Depends(get_db)):
    _validar_referencias(db, dados)
    garantir_unico(db, Disciplina, "codigo", dados.codigo, "CODIGO_JA_CADASTRADO", "Já existe uma disciplina com este código.")
    disciplina = Disciplina(**dados.model_dump())
    db.add(disciplina)
    db.commit()
    return disciplina


@router.get("/{disciplina_id}", response_model=DisciplinaDetalhe, dependencies=[Depends(CATALOGO)],
            summary="Buscar disciplina por id")
def buscar(disciplina_id: int, db: Session = Depends(get_db)):
    d = buscar_ou_404(db, Disciplina, disciplina_id, MSG_404)
    return {
        "id": d.id, "codigo": d.codigo, "nome": d.nome, "carga_horaria": d.carga_horaria,
        "semestre": d.semestre, "vagas": d.vagas, "vagas_ocupadas": vagas_ocupadas(db, d.id),
        "curso": {"id": d.curso.id, "nome": d.curso.nome},
        "professor": {"id": d.professor.id, "nome": d.professor.nome},
    }


@router.put("/{disciplina_id}", response_model=DisciplinaOut, dependencies=[Depends(ESCRITA)],
            summary="Atualizar disciplina")
def atualizar(disciplina_id: int, dados: DisciplinaIn, db: Session = Depends(get_db)):
    disciplina = buscar_ou_404(db, Disciplina, disciplina_id, MSG_404)
    _validar_referencias(db, dados)
    garantir_unico(db, Disciplina, "codigo", dados.codigo, "CODIGO_JA_CADASTRADO",
                   "Já existe uma disciplina com este código.", ignorar_id=disciplina_id)
    if dados.vagas < vagas_ocupadas(db, disciplina_id):
        raise AppError(409, "VAGAS_INSUFICIENTES", "O número de vagas não pode ser menor que o de vagas já ocupadas.")
    for campo, valor in dados.model_dump().items():
        setattr(disciplina, campo, valor)
    db.commit()
    return disciplina


@router.delete("/{disciplina_id}", status_code=204, dependencies=[Depends(ESCRITA)], summary="Remover disciplina")
def remover(disciplina_id: int, db: Session = Depends(get_db)):
    disciplina = buscar_ou_404(db, Disciplina, disciplina_id, MSG_404)
    if existe(db, Matricula.disciplina_id == disciplina_id):
        raise bloqueio_exclusao("A disciplina possui matrículas e não pode ser removida.")
    db.delete(disciplina)
    db.commit()
    return Response(status_code=204)


# ---------- relacionamento ----------
@router.get("/{disciplina_id}/matriculas", response_model=list[MatriculaDaDisciplina], dependencies=[Depends(EQUIPE)],
            summary="Listar os alunos matriculados em uma disciplina")
def matriculas_da_disciplina(disciplina_id: int, db: Session = Depends(get_db)):
    buscar_ou_404(db, Disciplina, disciplina_id, MSG_404)
    matriculas = db.scalars(
        select(Matricula).where(Matricula.disciplina_id == disciplina_id).order_by(Matricula.id)
    ).all()
    return [
        {
            "id": m.id, "aluno_id": m.aluno_id, "aluno": m.aluno.nome, "periodo": m.periodo,
            "nota_final": m.nota_final, "frequencia": m.frequencia, "situacao": m.situacao,
        }
        for m in matriculas
    ]
