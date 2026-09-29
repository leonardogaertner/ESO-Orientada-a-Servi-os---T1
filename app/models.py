from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Curso(Base):
    __tablename__ = "cursos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    duracao_semestres: Mapped[int]
    turno: Mapped[str] = mapped_column(String(20))

    alunos: Mapped[list["Aluno"]] = relationship(back_populates="curso")
    disciplinas: Mapped[list["Disciplina"]] = relationship(back_populates="curso")


class Professor(Base):
    __tablename__ = "professores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True)
    titulacao: Mapped[str] = mapped_column(String(20))

    disciplinas: Mapped[list["Disciplina"]] = relationship(back_populates="professor")


class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True)
    data_nascimento: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="ATIVO")
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"), index=True)

    curso: Mapped[Curso] = relationship(back_populates="alunos")
    matriculas: Mapped[list["Matricula"]] = relationship(back_populates="aluno")


class Disciplina(Base):
    __tablename__ = "disciplinas"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    carga_horaria: Mapped[int]
    semestre: Mapped[int]
    vagas: Mapped[int]
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"), index=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("professores.id"), index=True)

    curso: Mapped[Curso] = relationship(back_populates="disciplinas")
    professor: Mapped[Professor] = relationship(back_populates="disciplinas")
    matriculas: Mapped[list["Matricula"]] = relationship(back_populates="disciplina")


class Matricula(Base):
    __tablename__ = "matriculas"
    __table_args__ = (UniqueConstraint("aluno_id", "disciplina_id", "periodo", name="uq_matricula"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    disciplina_id: Mapped[int] = mapped_column(ForeignKey("disciplinas.id"), index=True)
    periodo: Mapped[str] = mapped_column(String(6))
    nota_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    frequencia: Mapped[float | None] = mapped_column(Float, nullable=True)
    situacao: Mapped[str] = mapped_column(String(20), default="CURSANDO")

    aluno: Mapped[Aluno] = relationship(back_populates="matriculas")
    disciplina: Mapped[Disciplina] = relationship(back_populates="matriculas")


class Usuario(Base):
    """Credenciais de acesso à API. Vinculado a um aluno ou professor conforme o perfil."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    perfil: Mapped[str] = mapped_column(String(20))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    aluno_id: Mapped[int | None] = mapped_column(ForeignKey("alunos.id"), nullable=True)
    professor_id: Mapped[int | None] = mapped_column(ForeignKey("professores.id"), nullable=True)


class TokenRevogado(Base):
    """Lista de tokens invalidados pelo logout (identificados pelo claim jti)."""

    __tablename__ = "tokens_revogados"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime)
