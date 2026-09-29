import os
import tempfile

# Banco isolado para os testes: precisa ser definido ANTES de importar a aplicação.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/teste.db"
os.environ["SECRET_KEY"] = "chave-de-teste-com-mais-de-trinta-e-dois-caracteres"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from tests.helpers import (criar_aluno, criar_curso, criar_disciplina, criar_professor,  # noqa: E402
                           criar_usuario, login)


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sec(client):
    criar_usuario("sec@faculdade.com.br", "SECRETARIA")
    return login(client, "sec@faculdade.com.br")


@pytest.fixture
def cenario(client, sec):
    """1 curso, 1 professor, 1 disciplina, 1 aluno + usuários (professor e aluno) vinculados."""
    curso = criar_curso(client, sec)
    prof = criar_professor(client, sec)
    disc = criar_disciplina(client, sec, curso["id"], prof["id"])
    aluno = criar_aluno(client, sec, curso["id"])
    criar_usuario("prof@faculdade.com.br", "PROFESSOR", professor_id=prof["id"])
    criar_usuario("aluno@faculdade.com.br", "ALUNO", aluno_id=aluno["id"])
    return {
        "curso": curso, "prof": prof, "disc": disc, "aluno": aluno,
        "h_prof": login(client, "prof@faculdade.com.br"),
        "h_aluno": login(client, "aluno@faculdade.com.br"),
    }
