from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .errors import registrar_handlers
from .routers import alunos, auth, cursos, disciplinas, matriculas, professores

DESCRICAO = """
API REST do **Sistema Acadêmico**: cursos, disciplinas, professores, alunos e matrículas.

**Como autenticar:** faça `POST /api/v1/auth/login`, copie o `token` e clique em **Authorize** (cadeado).
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="API Acadêmica", version="1.0.0", description=DESCRICAO, lifespan=lifespan)
registrar_handlers(app)

for roteador in (auth.router, cursos.router, professores.router, alunos.router, disciplinas.router, matriculas.router):
    app.include_router(roteador, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def raiz():
    return {"api": "API Acadêmica", "versao": "1.0.0", "documentacao": "/docs"}
