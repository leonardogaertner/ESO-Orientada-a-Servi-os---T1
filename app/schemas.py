import re
from datetime import date
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from .enums import Perfil, SituacaoMatricula, StatusAluno, Titulacao, Turno

# ---------- validações reutilizáveis ----------
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PERIODO_RE = re.compile(r"^\d{4}\.[12]$")


def _email(v: str) -> str:
    if not _EMAIL_RE.match(v):
        raise ValueError("Formato de e-mail inválido.")
    return v.lower()


def _cpf(v: str) -> str:
    if not re.fullmatch(r"\d{11}", v):
        raise ValueError("CPF deve conter 11 dígitos.")
    return v


def _periodo(v: str) -> str:
    if not _PERIODO_RE.match(v):
        raise ValueError("Período inválido. Use o formato AAAA.S (ex.: 2026.2).")
    return v


Email = Annotated[str, AfterValidator(_email)]
CPF = Annotated[str, AfterValidator(_cpf)]
Periodo = Annotated[str, AfterValidator(_periodo)]
Nome = Annotated[str, Field(min_length=2, max_length=120)]


class Entrada(BaseModel):
    model_config = ConfigDict(use_enum_values=True, str_strip_whitespace=True)


class Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    page: int
    limit: int
    total: int
    total_pages: int
    data: list[T]


# ---------- auth ----------
class LoginIn(Entrada):
    email: Annotated[str, Field(min_length=1)]
    senha: Annotated[str, Field(min_length=1)]


class LoginOut(BaseModel):
    token: str
    tipo: str
    expira_em: int
    perfil: Perfil


class MeOut(Saida):
    id: int
    email: str
    perfil: Perfil
    aluno_id: int | None
    professor_id: int | None


# ---------- cursos ----------
class CursoIn(Entrada):
    nome: Nome
    duracao_semestres: Annotated[int, Field(ge=1, le=20)]
    turno: Turno


class CursoOut(Saida):
    id: int
    nome: str
    duracao_semestres: int
    turno: Turno


class CursoResumo(Saida):
    id: int
    nome: str


# ---------- professores ----------
class ProfessorIn(Entrada):
    nome: Nome
    email: Email
    cpf: CPF
    titulacao: Titulacao


class ProfessorOut(Saida):
    id: int
    nome: str
    email: str
    titulacao: Titulacao


class ProfessorResumo(Saida):
    id: int
    nome: str


# ---------- alunos ----------
class AlunoIn(Entrada):
    nome: Nome
    email: Email
    cpf: CPF
    data_nascimento: date
    curso_id: int


class AlunoUpdate(AlunoIn):
    status: StatusAluno | None = None  # se omitido, mantém o status atual


class AlunoOut(Saida):
    id: int
    matricula: str
    nome: str
    email: str
    curso_id: int
    status: StatusAluno


class AlunoDetalhe(Saida):
    id: int
    matricula: str
    nome: str
    email: str
    data_nascimento: date
    curso: CursoResumo
    status: StatusAluno


class AlunoResumo(Saida):
    id: int
    matricula: str
    nome: str


# ---------- disciplinas ----------
class DisciplinaIn(Entrada):
    codigo: Annotated[str, Field(min_length=2, max_length=20)]
    nome: Nome
    carga_horaria: Annotated[int, Field(ge=1)]
    semestre: Annotated[int, Field(ge=1, le=20)]
    vagas: Annotated[int, Field(ge=1)]
    curso_id: int
    professor_id: int


class DisciplinaOut(Saida):
    id: int
    codigo: str
    nome: str
    carga_horaria: int
    semestre: int
    vagas: int
    curso_id: int
    professor_id: int


class DisciplinaDetalhe(Saida):
    id: int
    codigo: str
    nome: str
    carga_horaria: int
    semestre: int
    vagas: int
    vagas_ocupadas: int
    curso: CursoResumo
    professor: ProfessorResumo


class DisciplinaListada(Saida):
    """Formato usado nos endpoints de relacionamento (ex.: /cursos/{id}/disciplinas)."""

    id: int
    codigo: str
    nome: str
    carga_horaria: int
    semestre: int


class DisciplinaMinima(Saida):
    id: int
    codigo: str
    nome: str


# ---------- matrículas ----------
class MatriculaIn(Entrada):
    aluno_id: int
    disciplina_id: int
    periodo: Periodo


class MatriculaUpdate(Entrada):
    periodo: Periodo
    situacao: SituacaoMatricula | None = None  # apenas CURSANDO ou TRANCADA


class NotasIn(Entrada):
    nota_final: float
    frequencia: float


class MatriculaOut(Saida):
    id: int
    aluno_id: int
    disciplina_id: int
    periodo: str
    nota_final: float | None
    frequencia: float | None
    situacao: SituacaoMatricula


class MatriculaDetalhe(Saida):
    id: int
    aluno: AlunoResumo
    disciplina: DisciplinaMinima
    periodo: str
    nota_final: float | None
    frequencia: float | None
    situacao: SituacaoMatricula


class NotasOut(Saida):
    id: int
    nota_final: float
    frequencia: float
    situacao: SituacaoMatricula


class MatriculaDoAluno(BaseModel):
    id: int
    disciplina_id: int
    disciplina: str
    periodo: str
    nota_final: float | None
    situacao: SituacaoMatricula


class MatriculaDaDisciplina(BaseModel):
    id: int
    aluno_id: int
    aluno: str
    periodo: str
    nota_final: float | None
    frequencia: float | None
    situacao: SituacaoMatricula
