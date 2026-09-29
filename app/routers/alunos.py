from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy import Integer, cast, delete, func, select
from sqlalchemy.orm import Session

from ..common import Paginacao, bloqueio_exclusao, buscar_ou_404, existe, garantir_unico, ordenar, paginar
from ..database import get_db
from ..deps import CATALOGO, EQUIPE, ESCRITA, exige_proprio_aluno
from ..enums import StatusAluno
from ..models import Aluno, Curso, Matricula, Usuario
from ..schemas import AlunoDetalhe, AlunoIn, AlunoOut, AlunoUpdate, MatriculaDoAluno, Pagina

router = APIRouter(prefix="/alunos", tags=["Alunos"])
MSG_404 = "Aluno não encontrado."


def _proxima_matricula(db: Session) -> str:
    """Número de matrícula no formato AAAASSS (ex.: 2026001)."""
    ano = date.today().year
    ultimo = db.scalar(
        select(func.max(cast(func.substr(Aluno.matricula, 5), Integer))).where(Aluno.matricula.like(f"{ano}%"))
    )
    return f"{ano}{(ultimo or 0) + 1:03d}"


def _checar_unicos(db: Session, dados: AlunoIn, ignorar_id: int | None = None):
    garantir_unico(db, Aluno, "cpf", dados.cpf, "CPF_JA_CADASTRADO", "Já existe um aluno com este CPF.", ignorar_id)
    garantir_unico(db, Aluno, "email", dados.email, "EMAIL_JA_CADASTRADO", "Já existe um aluno com este e-mail.", ignorar_id)


@router.get("", response_model=Pagina[AlunoOut], dependencies=[Depends(EQUIPE)],
            summary="Listar alunos (filtros e paginação)")
def listar(
    nome: str | None = None,
    curso_id: int | None = None,
    status: StatusAluno | None = None,
    sort: str | None = None,
    p: Paginacao = Depends(),
    db: Session = Depends(get_db),
):
    stmt = select(Aluno)
    if nome:
        stmt = stmt.where(Aluno.nome.ilike(f"%{nome}%"))
    if curso_id is not None:
        stmt = stmt.where(Aluno.curso_id == curso_id)
    if status:
        stmt = stmt.where(Aluno.status == status.value)
    stmt = ordenar(stmt, Aluno, sort, {"id", "nome", "matricula", "email", "status"})
    return paginar(db, stmt, p)


@router.post("", response_model=AlunoOut, status_code=201, dependencies=[Depends(ESCRITA)],
             summary="Cadastrar aluno")
def criar(dados: AlunoIn, db: Session = Depends(get_db)):
    buscar_ou_404(db, Curso, dados.curso_id, "Curso não encontrado.")
    _checar_unicos(db, dados)
    aluno = Aluno(matricula=_proxima_matricula(db), status=StatusAluno.ATIVO.value, **dados.model_dump())
    db.add(aluno)
    db.commit()
    return aluno


@router.get("/{aluno_id}", response_model=AlunoDetalhe, summary="Buscar aluno por id")
def buscar(aluno_id: int, usuario: Usuario = Depends(CATALOGO), db: Session = Depends(get_db)):
    exige_proprio_aluno(usuario, aluno_id)
    aluno = buscar_ou_404(db, Aluno, aluno_id, MSG_404)
    return {
        "id": aluno.id, "matricula": aluno.matricula, "nome": aluno.nome, "email": aluno.email,
        "data_nascimento": aluno.data_nascimento, "status": aluno.status,
        "curso": {"id": aluno.curso.id, "nome": aluno.curso.nome},
    }


@router.put("/{aluno_id}", response_model=AlunoOut, dependencies=[Depends(ESCRITA)], summary="Atualizar aluno")
def atualizar(aluno_id: int, dados: AlunoUpdate, db: Session = Depends(get_db)):
    aluno = buscar_ou_404(db, Aluno, aluno_id, MSG_404)
    buscar_ou_404(db, Curso, dados.curso_id, "Curso não encontrado.")
    _checar_unicos(db, dados, ignorar_id=aluno_id)
    valores = dados.model_dump(exclude_none=True)  # status omitido => mantém o atual
    for campo, valor in valores.items():
        setattr(aluno, campo, valor)
    db.commit()
    return aluno


@router.delete("/{aluno_id}", status_code=204, dependencies=[Depends(ESCRITA)], summary="Remover aluno")
def remover(aluno_id: int, db: Session = Depends(get_db)):
    aluno = buscar_ou_404(db, Aluno, aluno_id, MSG_404)
    if existe(db, Matricula.aluno_id == aluno_id):
        raise bloqueio_exclusao("O aluno possui matrículas e não pode ser removido. Altere o status para INATIVO.")
    db.execute(delete(Usuario).where(Usuario.aluno_id == aluno_id))  # remove também o login vinculado
    db.delete(aluno)
    db.commit()
    return Response(status_code=204)


# ---------- relacionamento ----------
@router.get("/{aluno_id}/matriculas", response_model=list[MatriculaDoAluno], summary="Histórico de matrículas do aluno")
def matriculas_do_aluno(aluno_id: int, usuario: Usuario = Depends(CATALOGO), db: Session = Depends(get_db)):
    exige_proprio_aluno(usuario, aluno_id)
    buscar_ou_404(db, Aluno, aluno_id, MSG_404)
    matriculas = db.scalars(select(Matricula).where(Matricula.aluno_id == aluno_id).order_by(Matricula.id)).all()
    return [
        {
            "id": m.id, "disciplina_id": m.disciplina_id, "disciplina": m.disciplina.nome,
            "periodo": m.periodo, "nota_final": m.nota_final, "situacao": m.situacao,
        }
        for m in matriculas
    ]
