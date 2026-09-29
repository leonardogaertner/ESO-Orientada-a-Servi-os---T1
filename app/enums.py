from enum import Enum


class Turno(str, Enum):
    MATUTINO = "MATUTINO"
    VESPERTINO = "VESPERTINO"
    NOTURNO = "NOTURNO"
    INTEGRAL = "INTEGRAL"


class Titulacao(str, Enum):
    GRADUADO = "GRADUADO"
    ESPECIALISTA = "ESPECIALISTA"
    MESTRE = "MESTRE"
    DOUTOR = "DOUTOR"


class StatusAluno(str, Enum):
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"
    TRANCADO = "TRANCADO"
    FORMADO = "FORMADO"


class SituacaoMatricula(str, Enum):
    CURSANDO = "CURSANDO"
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"
    TRANCADA = "TRANCADA"


class Perfil(str, Enum):
    ADMIN = "ADMIN"
    SECRETARIA = "SECRETARIA"
    PROFESSOR = "PROFESSOR"
    ALUNO = "ALUNO"
