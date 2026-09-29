from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common import Paginacao, buscar_ou_404, existe, ordenar, paginar, vagas_ocupadas
from ..config import FREQUENCIA_MINIMA, NOTA_MINIMA
from ..database import get_db
from ..deps import CATALOGO, EQUIPE, ESCRITA, exige, exige_proprio_aluno
from ..enums import Perfil, SituacaoMatricula
from ..errors import AppError
from ..models import Aluno, Disciplina, Matricula, Usuario
from ..schemas import MatriculaDetalhe, MatriculaIn, MatriculaOut, MatriculaUpdate, NotasIn, NotasOut, Pagina

router = APIRouter(prefix="/matriculas", tags=["Matrículas"])
MSG_404 = "Matrícula não encontrada."
ENCERRADAS = (SituacaoMatricula.APROVADO.value, SituacaoMatricula.REPROVADO.value)


def _duplicada(db: Session, aluno_id: int, disciplina_id: int, periodo: str, ignorar_id: int | None = None) -> bool:
    cond = (Matricula.aluno_id == aluno_id) & (Matricula.disciplina_id == disciplina_id) & (Matricula.periodo == periodo)
    if ignorar_id is not None:
        cond = cond & (Matricula.id != ignorar_id)
    return existe(db, cond)


def _sem_vagas(db: Session, disciplina: Disciplina) -> bool:
    return vagas_ocupadas(db, disciplina.id) >= disciplina.vagas


@router.get("", response_model=Pagina[MatriculaOut], dependencies=[Depends(EQUIPE)],
            summary="Listar matrículas (filtros e paginação)")
def listar(
    periodo: str | None = None,
    situacao: SituacaoMatricula | None = None,
    aluno_id: int | None = None,
    disciplina_id: int | None = None,
    sort: str | None = None,
    p: Paginacao = Depends(),
    db: Session = Depends(get_db),
):
    stmt = select(Matricula)
    if periodo:
        stmt = stmt.where(Matricula.periodo == periodo)
    if situacao:
        stmt = stmt.where(Matricula.situacao == situacao.value)
    if aluno_id is not None:
        stmt = stmt.where(Matricula.aluno_id == aluno_id)
    if disciplina_id is not None:
        stmt = stmt.where(Matricula.disciplina_id == disciplina_id)
    stmt = ordenar(stmt, Matricula, sort, {"id", "periodo", "situacao", "nota_final"})
    return paginar(db, stmt, p)


@router.post("", response_model=MatriculaOut, status_code=201, summary="Matricular aluno em disciplina")
def criar(
    dados: MatriculaIn,
    usuario: Usuario = Depends(exige(Perfil.SECRETARIA, Perfil.ALUNO)),
    db: Session = Depends(get_db),
):
    if usuario.perfil == Perfil.ALUNO.value and usuario.aluno_id != dados.aluno_id:
        raise AppError(403, "ACESSO_NEGADO", "Você só pode se matricular em seu próprio nome.")
    aluno = buscar_ou_404(db, Aluno, dados.aluno_id, "Aluno não encontrado.")
    disciplina = buscar_ou_404(db, Disciplina, dados.disciplina_id, "Disciplina não encontrada.")
    if aluno.status != "ATIVO":
        raise AppError(409, "ALUNO_INATIVO", "O aluno não está ativo e não pode ser matriculado.")
    if _duplicada(db, aluno.id, disciplina.id, dados.periodo):
        raise AppError(409, "MATRICULA_DUPLICADA", "O aluno já está matriculado nesta disciplina no período.")
    if _sem_vagas(db, disciplina):
        raise AppError(409, "VAGAS_ESGOTADAS", "Não há vagas disponíveis nesta disciplina.")
    matricula = Matricula(
        aluno_id=aluno.id, disciplina_id=disciplina.id, periodo=dados.periodo,
        situacao=SituacaoMatricula.CURSANDO.value,
    )
    db.add(matricula)
    db.commit()
    return matricula


@router.get("/{matricula_id}", response_model=MatriculaDetalhe, summary="Buscar matrícula por id")
def buscar(matricula_id: int, usuario: Usuario = Depends(CATALOGO), db: Session = Depends(get_db)):
    m = buscar_ou_404(db, Matricula, matricula_id, MSG_404)
    exige_proprio_aluno(usuario, m.aluno_id)
    return {
        "id": m.id, "periodo": m.periodo, "nota_final": m.nota_final,
        "frequencia": m.frequencia, "situacao": m.situacao,
        "aluno": {"id": m.aluno.id, "matricula": m.aluno.matricula, "nome": m.aluno.nome},
        "disciplina": {"id": m.disciplina.id, "codigo": m.disciplina.codigo, "nome": m.disciplina.nome},
    }


@router.put("/{matricula_id}", response_model=MatriculaOut, dependencies=[Depends(ESCRITA)],
            summary="Atualizar matrícula (período e/ou trancamento)")
def atualizar(matricula_id: int, dados: MatriculaUpdate, db: Session = Depends(get_db)):
    m = buscar_ou_404(db, Matricula, matricula_id, MSG_404)
    if m.situacao in ENCERRADAS:
        raise AppError(409, "MATRICULA_ENCERRADA", "A matrícula já foi encerrada e não pode ser alterada.")
    nova = dados.situacao or m.situacao
    if nova not in (SituacaoMatricula.CURSANDO.value, SituacaoMatricula.TRANCADA.value):
        raise AppError(
            400, "SITUACAO_INVALIDA",
            "Por aqui só é possível definir CURSANDO ou TRANCADA. APROVADO/REPROVADO são definidos ao lançar as notas.",
        )
    if dados.periodo != m.periodo and _duplicada(db, m.aluno_id, m.disciplina_id, dados.periodo, ignorar_id=m.id):
        raise AppError(409, "MATRICULA_DUPLICADA", "O aluno já está matriculado nesta disciplina no período.")
    if m.situacao == SituacaoMatricula.TRANCADA.value and nova == SituacaoMatricula.CURSANDO.value \
            and _sem_vagas(db, m.disciplina):
        raise AppError(409, "VAGAS_ESGOTADAS", "Não há vagas disponíveis nesta disciplina.")
    m.periodo = dados.periodo
    m.situacao = nova
    db.commit()
    return m


@router.delete("/{matricula_id}", status_code=204, dependencies=[Depends(ESCRITA)], summary="Cancelar matrícula")
def remover(matricula_id: int, db: Session = Depends(get_db)):
    m = buscar_ou_404(db, Matricula, matricula_id, MSG_404)
    if m.situacao in ENCERRADAS:
        raise AppError(409, "MATRICULA_ENCERRADA", "Não é possível cancelar uma matrícula de disciplina já encerrada.")
    db.delete(m)
    db.commit()
    return Response(status_code=204)


@router.patch("/{matricula_id}/notas", response_model=NotasOut, summary="Lançar nota e frequência")
def lancar_notas(
    matricula_id: int,
    dados: NotasIn,
    usuario: Usuario = Depends(exige(Perfil.SECRETARIA, Perfil.PROFESSOR)),
    db: Session = Depends(get_db),
):
    m = buscar_ou_404(db, Matricula, matricula_id, MSG_404)
    if usuario.perfil == Perfil.PROFESSOR.value and m.disciplina.professor_id != usuario.professor_id:
        raise AppError(403, "ACESSO_NEGADO", "Você só pode lançar notas nas suas próprias disciplinas.")
    if m.situacao == SituacaoMatricula.TRANCADA.value:
        raise AppError(409, "MATRICULA_TRANCADA", "Não é possível lançar notas em uma matrícula trancada.")
    if not 0 <= dados.nota_final <= 10:
        raise AppError(400, "NOTA_INVALIDA", "A nota deve estar entre 0 e 10.")
    if not 0 <= dados.frequencia <= 100:
        raise AppError(400, "FREQUENCIA_INVALIDA", "A frequência deve estar entre 0 e 100.")
    m.nota_final = dados.nota_final
    m.frequencia = dados.frequencia
    aprovado = dados.nota_final >= NOTA_MINIMA and dados.frequencia >= FREQUENCIA_MINIMA
    m.situacao = (SituacaoMatricula.APROVADO if aprovado else SituacaoMatricula.REPROVADO).value
    db.commit()
    return m
