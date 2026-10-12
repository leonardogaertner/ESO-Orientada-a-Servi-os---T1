# API Acadêmica (FastAPI)

Implementação da especificação REST do Sistema Acadêmico: cursos, professores, alunos, disciplinas e matrículas,
com autenticação JWT, filtros, paginação, relacionamentos e tratamento de erros padronizado.

**Stack:** Python 3.10+ · FastAPI · SQLAlchemy 2 · SQLite (padrão) · PyJWT · pytest

## Como rodar (Windows — CMD)

**Pré-requisito:** Python 3.10 ou mais novo. Confira com `python --version`. Se não tiver, instale em
python.org e marque **"Add python.exe to PATH"** na instalação.

Abra o **Prompt de Comando (CMD)** e siga na ordem:

**1. Entre na pasta do projeto** (a que contém `requirements.txt` e `seed.py`):

```bat
cd C:\caminho\para\academico_api
```

**2. Crie o ambiente virtual** (só na primeira vez):

```bat
python -m venv .venv
```

**3. Ative o ambiente virtual** (a cada novo CMD aberto):

```bat
.venv\Scripts\activate.bat
```

O prompt deve passar a começar com `(.venv)`. Se não aparecer, o ambiente não foi ativado.

**4. Instale as dependências** (só na primeira vez):

```bat
python -m pip install -r requirements.txt
```

**5. Crie o banco e os dados de demonstração** (só na primeira vez):

```bat
python seed.py
```

Ele lista os usuários de demonstração (tabela abaixo).

**6. Suba a API:**

```bat
python -m uvicorn app.main:app --reload
```

**7. Abra o Swagger no navegador:** http://127.0.0.1:8000/docs

- Abra `POST /api/v1/auth/login`, clique em **Try it out** e envie
  `{"email": "secretaria@faculdade.com.br", "senha": "123456"}`.
- Copie o valor de `token` da resposta, clique em **Authorize** (cadeado) e cole o token.
- Pronto: todos os endpoints passam a funcionar pelo Swagger.

**8. Para parar a API:** `Ctrl+C` no CMD.

**Nas próximas vezes** só são necessários os passos 1, 3 e 6.

| Perfil | E-mail | Senha |
|---|---|---|
| ADMIN | admin@faculdade.com.br | admin123 |
| SECRETARIA | secretaria@faculdade.com.br | 123456 |
| PROFESSOR | professor@faculdade.com.br | 123456 |
| ALUNO | aluno@faculdade.com.br | 123456 |

> Usuários de demonstração: **não use em produção**.

### Problemas comuns

| Problema | Solução |
|---|---|
| `No module named 'sqlalchemy'` (ou outro módulo) | O ambiente virtual não está ativo, ou o `pip` instalou em outro Python. Ative com `.venv\Scripts\activate.bat` (confira o `(.venv)` no prompt) e instale com `python -m pip install -r requirements.txt`. |
| `Activate.ps1` não funciona no CMD | Esse arquivo é só do PowerShell. No CMD use `.venv\Scripts\activate.bat`. |
| `'python' não é reconhecido` | Tente `py` no lugar de `python` (ex.: `py -m venv .venv`). Ou reinstale o Python marcando "Add python.exe to PATH". |
| Porta 8000 em uso | Use outra porta: `python -m uvicorn app.main:app --reload --port 8001` (e abra `http://127.0.0.1:8001/docs`). |
| Quero zerar o banco | Pare a API, rode `del academico.db` e depois `python seed.py` de novo. |
| `401 TOKEN_INVALIDO` no Swagger | O token expirou (2 h) ou você fez logout. Faça login de novo e cole o novo token em **Authorize**. |

### PowerShell, Linux e Mac

- **PowerShell:** use `.venv\Scripts\Activate.ps1` no passo 3. Se aparecer "execução de scripts desabilitada",
  rode `Set-ExecutionPolicy -Scope Process Bypass` e tente de novo.
- **Linux/Mac:** use `python3` no lugar de `python` e `source .venv/bin/activate` no passo 3.

## Testes

Com o ambiente virtual ativo:

```bat
python -m pytest -q
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
