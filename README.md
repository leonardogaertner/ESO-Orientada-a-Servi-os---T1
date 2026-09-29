# API Acadêmica (FastAPI)

Implementação da especificação REST do Sistema Acadêmico: cursos, professores, alunos, disciplinas e matrículas,
com autenticação JWT, filtros, paginação, relacionamentos e tratamento de erros padronizado.

**Stack:** Python 3.10+ · FastAPI · SQLAlchemy 2 · SQLite (padrão) · PyJWT · pytest

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed.py                     # cria o banco e dados/usuários de demonstração
uvicorn app.main:app --reload      # http://127.0.0.1:8000/docs
```

No Swagger (`/docs`): faça `POST /api/v1/auth/login`, copie o `token` e clique em **Authorize**.

| Perfil | E-mail | Senha |
|---|---|---|
| ADMIN | admin@faculdade.com.br | admin123 |
| SECRETARIA | secretaria@faculdade.com.br | 123456 |
| PROFESSOR | professor@faculdade.com.br | 123456 |
| ALUNO | aluno@faculdade.com.br | 123456 |

> Usuários de demonstração: **não use em produção**.

## Testes

```bash
pytest -q
```

## Estrutura

```
app/
  main.py         # aplicação, routers e handlers
  config.py       # configurações (variáveis de ambiente) e regras de aprovação
  database.py     # engine, sessão e Base
  models.py       # tabelas (SQLAlchemy)
  schemas.py      # entrada/saída e validações (Pydantic)
  security.py     # hash de senha (PBKDF2) e JWT
  deps.py         # autenticação e autorização por perfil
  errors.py       # padrão de erro da API
  common.py       # paginação, ordenação, checagens reutilizáveis
  routers/        # auth, cursos, professores, alunos, disciplinas, matriculas
seed.py           # dados de demonstração
tests/            # testes automatizados (pytest)
```

## Configuração (variáveis de ambiente)

| Variável | Padrão | Uso |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./academico.db` | Banco (ex.: `postgresql+psycopg://user:senha@host/db`) |
| `SECRET_KEY` | chave de desenvolvimento | **Defina uma chave própria (32+ caracteres) em produção** |
| `TOKEN_EXPIRE_SECONDS` | `7200` | Validade do token (2 h) |

## Permissões por perfil

| Perfil | Pode |
|---|---|
| `ADMIN` | Tudo |
| `SECRETARIA` | CRUD de todos os recursos; lançar notas |
| `PROFESSOR` | Leitura geral; lançar notas (`PATCH /matriculas/{id}/notas`) só nas próprias disciplinas |
| `ALUNO` | Ler os próprios dados e matrículas; ler cursos e disciplinas; matricular-se (só em seu nome) |

## Regras de negócio

- Aprovado se `nota_final ≥ 6.0` **e** `frequencia ≥ 75`; caso contrário, reprovado.
- Nota válida: 0–10 (`NOTA_INVALIDA`); frequência: 0–100 (`FREQUENCIA_INVALIDA`).
- `vagas_ocupadas` = matrículas `CURSANDO` na disciplina; sem vaga → `VAGAS_ESGOTADAS`.
- Não repete matrícula (aluno + disciplina + período) → `MATRICULA_DUPLICADA`; só aluno `ATIVO` se matricula.
- `PUT /matriculas/{id}` altera o período e/ou a situação (`CURSANDO` ↔ `TRANCADA`). Matrícula encerrada
  (aprovado/reprovado) não pode ser alterada nem cancelada.
- Não se remove curso com alunos/disciplinas, professor com disciplinas, disciplina ou aluno com matrículas
  (`EXCLUSAO_BLOQUEADA`). Ao remover aluno/professor, o login vinculado também é removido.
- Número de matrícula do aluno gerado automaticamente (`AAAASSS`, ex.: `2026001`).

## Erros

Formato único; validações trazem `detalhes` por campo.

```json
{
  "status": 404,
  "erro": "RECURSO_NAO_ENCONTRADO",
  "mensagem": "Aluno não encontrado.",
  "caminho": "/api/v1/alunos/999",
  "timestamp": "2026-09-29T14:30:00Z"
}
```

Códigos usados: 400, 401, 403, 404, 409 e 500.

## Observações

- As tabelas são criadas automaticamente na inicialização (`create_all`). Para evoluir o schema em produção,
  o próximo passo natural é adotar migrações (Alembic).
- Não há endpoint para criar usuários de login: eles são criados pelo `seed.py` (ou direto no banco).
