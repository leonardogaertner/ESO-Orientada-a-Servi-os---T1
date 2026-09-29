from tests.helpers import (API, SENHA, criar_aluno, criar_curso, criar_disciplina, criar_professor,
                           criar_usuario, login, matricular)


# ============ autenticação ============
def test_login_ok_e_me(client, sec):
    r = client.post(f"{API}/auth/login", json={"email": "sec@faculdade.com.br", "senha": SENHA})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["tipo"] == "Bearer" and corpo["expira_em"] == 7200 and corpo["perfil"] == "SECRETARIA"
    me = client.get(f"{API}/auth/me", headers=sec)
    assert me.status_code == 200 and me.json()["email"] == "sec@faculdade.com.br"


def test_login_senha_errada_401(client, sec):
    r = client.post(f"{API}/auth/login", json={"email": "sec@faculdade.com.br", "senha": "errada"})
    assert r.status_code == 401
    assert r.json()["erro"] == "CREDENCIAIS_INVALIDAS"
    assert r.json()["mensagem"] == "E-mail ou senha incorretos."


def test_sem_token_ou_token_invalido_401(client):
    for headers in ({}, {"Authorization": "Bearer lixo"}, {"Authorization": "Basic abc"}):
        r = client.get(f"{API}/cursos", headers=headers)
        assert r.status_code == 401, headers
        assert r.json()["erro"] == "TOKEN_INVALIDO"


def test_logout_revoga_token(client, sec):
    assert client.post(f"{API}/auth/logout", headers=sec).status_code == 204
    r = client.get(f"{API}/auth/me", headers=sec)
    assert r.status_code == 401 and r.json()["erro"] == "TOKEN_INVALIDO"


# ============ CRUD + formato de erro ============
def test_crud_curso_completo(client, sec):
    c = criar_curso(client, sec)
    assert set(c) == {"id", "nome", "duracao_semestres", "turno"}
    assert client.get(f"{API}/cursos/{c['id']}", headers=sec).json() == c

    r = client.put(f"{API}/cursos/{c['id']}", headers=sec,
                   json={"nome": "Eng. de Software", "duracao_semestres": 8, "turno": "INTEGRAL"})
    assert r.status_code == 200 and r.json()["duracao_semestres"] == 8

    assert client.delete(f"{API}/cursos/{c['id']}", headers=sec).status_code == 204
    r = client.get(f"{API}/cursos/{c['id']}", headers=sec)
    assert r.status_code == 404
    corpo = r.json()
    assert corpo["status"] == 404 and corpo["erro"] == "RECURSO_NAO_ENCONTRADO"
    assert corpo["mensagem"] == "Curso não encontrado."
    assert corpo["caminho"] == f"{API}/cursos/{c['id']}" and corpo["timestamp"].endswith("Z")


def test_crud_professor_aluno_disciplina(client, sec, cenario):
    prof, aluno, disc = cenario["prof"], cenario["aluno"], cenario["disc"]
    assert "cpf" not in prof  # CPF não é devolvido
    assert aluno["matricula"].endswith("001") and aluno["status"] == "ATIVO"

    det = client.get(f"{API}/alunos/{aluno['id']}", headers=sec).json()
    assert det["curso"] == {"id": cenario["curso"]["id"], "nome": "Engenharia de Software"}
    assert det["data_nascimento"] == "2003-05-14"

    det = client.get(f"{API}/disciplinas/{disc['id']}", headers=sec).json()
    assert det["vagas_ocupadas"] == 0 and det["professor"]["id"] == prof["id"]

    r = client.put(f"{API}/alunos/{aluno['id']}", headers=sec, json={
        "nome": "Aluno Editado", "email": "novo@email.com", "cpf": "00000050001",
        "data_nascimento": "2003-05-14", "curso_id": cenario["curso"]["id"], "status": "TRANCADO"})
    assert r.status_code == 200 and r.json()["status"] == "TRANCADO" and r.json()["nome"] == "Aluno Editado"

    r = client.put(f"{API}/professores/{prof['id']}", headers=sec, json={
        "nome": "Prof Novo", "email": "novo.prof@faculdade.com.br", "cpf": "00000000001", "titulacao": "DOUTOR"})
    assert r.status_code == 200 and r.json()["titulacao"] == "DOUTOR"

    # aluno sem matrículas pode ser removido; o login vinculado a ele deixa de valer
    assert client.get(f"{API}/auth/me", headers=cenario["h_aluno"]).status_code == 200
    assert client.delete(f"{API}/alunos/{aluno['id']}", headers=sec).status_code == 204
    assert client.get(f"{API}/auth/me", headers=cenario["h_aluno"]).status_code == 401


def test_matricula_numero_sequencial(client, sec):
    curso = criar_curso(client, sec)
    m = [criar_aluno(client, sec, curso["id"], n)["matricula"] for n in (1, 2, 3)]
    assert [x[4:] for x in m] == ["001", "002", "003"]


# ============ erros ============
def test_validacao_400_com_detalhes(client, sec, cenario):
    r = client.post(f"{API}/alunos", headers=sec, json={
        "nome": "Fulano", "email": "isso-nao-e-email", "cpf": "123", "data_nascimento": "2003-05-14",
        "curso_id": cenario["curso"]["id"]})
    assert r.status_code == 400
    corpo = r.json()
    assert corpo["erro"] == "DADOS_INVALIDOS"
    detalhes = {d["campo"]: d["problema"] for d in corpo["detalhes"]}
    assert detalhes["email"] == "Formato de e-mail inválido."
    assert detalhes["cpf"] == "CPF deve conter 11 dígitos."

    r = client.post(f"{API}/alunos", headers=sec, json={})
    assert {d["campo"] for d in r.json()["detalhes"]} >= {"nome", "email", "cpf", "curso_id"}
    assert client.post(f"{API}/cursos", headers=sec, content="{quebrado").status_code == 400


def test_referencia_inexistente_404(client, sec):
    r = client.post(f"{API}/alunos", headers=sec, json={
        "nome": "Fulano", "email": "f@email.com", "cpf": "12345678901", "data_nascimento": "2003-05-14",
        "curso_id": 999})
    assert r.status_code == 404 and r.json()["mensagem"] == "Curso não encontrado."


def test_cpf_e_email_duplicados_409(client, sec, cenario):
    base = {"nome": "Outro", "email": "outro@email.com", "cpf": "00000050001", "data_nascimento": "2003-05-14",
            "curso_id": cenario["curso"]["id"]}
    r = client.post(f"{API}/alunos", headers=sec, json=base)
    assert r.status_code == 409 and r.json()["erro"] == "CPF_JA_CADASTRADO"
    r = client.post(f"{API}/alunos", headers=sec, json={**base, "cpf": "11111111111", "email": "aluno1@email.com"})
    assert r.status_code == 409 and r.json()["erro"] == "EMAIL_JA_CADASTRADO"
    r = client.post(f"{API}/disciplinas", headers=sec, json={
        "codigo": "ENG204", "nome": "Disciplina repetida", "carga_horaria": 30, "semestre": 1, "vagas": 10,
        "curso_id": cenario["curso"]["id"], "professor_id": cenario["prof"]["id"]})
    assert r.status_code == 409 and r.json()["erro"] == "CODIGO_JA_CADASTRADO"


def test_exclusao_bloqueada_409(client, sec, cenario):
    assert matricular(client, sec, cenario["aluno"]["id"], cenario["disc"]["id"]).status_code == 201
    for rota in (f"cursos/{cenario['curso']['id']}", f"professores/{cenario['prof']['id']}",
                 f"disciplinas/{cenario['disc']['id']}", f"alunos/{cenario['aluno']['id']}"):
        r = client.delete(f"{API}/{rota}", headers=sec)
        assert r.status_code == 409 and r.json()["erro"] == "EXCLUSAO_BLOQUEADA", rota


def test_rota_inexistente_404_e_erro_500(client, sec):
    r = client.get(f"{API}/nao-existe", headers=sec)
    assert r.status_code == 404 and r.json()["erro"] == "RECURSO_NAO_ENCONTRADO"

    from fastapi.testclient import TestClient
    from app.main import app

    @app.get("/_explode", include_in_schema=False)
    def explode():
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/_explode")
    assert r.status_code == 500
    assert r.json()["erro"] == "ERRO_INTERNO" and "boom" not in r.text


# ============ relacionamentos ============
def test_relacionamentos(client, sec, cenario):
    curso, prof, disc, aluno = cenario["curso"], cenario["prof"], cenario["disc"], cenario["aluno"]
    m = matricular(client, sec, aluno["id"], disc["id"]).json()

    r = client.get(f"{API}/cursos/{curso['id']}/alunos", headers=sec)
    assert [a["id"] for a in r.json()] == [aluno["id"]]

    r = client.get(f"{API}/cursos/{curso['id']}/disciplinas", headers=sec)
    assert r.json() == [{"id": disc["id"], "codigo": "ENG204", "nome": "Disciplina ENG204",
                         "carga_horaria": 60, "semestre": 5}]

    r = client.get(f"{API}/professores/{prof['id']}/disciplinas", headers=sec)
    assert [d["id"] for d in r.json()] == [disc["id"]]

    r = client.get(f"{API}/alunos/{aluno['id']}/matriculas", headers=sec)
    assert r.json() == [{"id": m["id"], "disciplina_id": disc["id"], "disciplina": "Disciplina ENG204",
                         "periodo": "2026.2", "nota_final": None, "situacao": "CURSANDO"}]

    r = client.get(f"{API}/disciplinas/{disc['id']}/matriculas", headers=sec)
    assert r.json()[0]["aluno"] == "Aluno 1" and r.json()[0]["aluno_id"] == aluno["id"]

    for rota in ("cursos", "professores", "alunos", "disciplinas"):
        sufixo = "disciplinas" if rota in ("cursos", "professores") else "matriculas"
        assert client.get(f"{API}/{rota}/9999/{sufixo}", headers=sec).status_code == 404


# ============ filtros, ordenação e paginação ============
def test_paginacao(client, sec):
    curso = criar_curso(client, sec)
    for n in range(1, 13):
        criar_aluno(client, sec, curso["id"], n)

    r = client.get(f"{API}/alunos?page=2&limit=5", headers=sec).json()
    assert (r["page"], r["limit"], r["total"], r["total_pages"], len(r["data"])) == (2, 5, 12, 3, 5)
    r = client.get(f"{API}/alunos?page=3&limit=5", headers=sec).json()
    assert len(r["data"]) == 2
    r = client.get(f"{API}/alunos?page=99&limit=5", headers=sec).json()
    assert r["data"] == [] and r["total"] == 12

    default = client.get(f"{API}/alunos", headers=sec).json()
    assert default["page"] == 1 and default["limit"] == 10 and len(default["data"]) == 10

    for qs in ("page=0", "limit=500", "limit=0", "page=abc"):
        r = client.get(f"{API}/alunos?{qs}", headers=sec)
        assert r.status_code == 400 and r.json()["erro"] == "DADOS_INVALIDOS", qs


def test_filtros_e_ordenacao(client, sec):
    c1, c2 = criar_curso(client, sec, "Curso A"), criar_curso(client, sec, "Curso B")
    criar_aluno(client, sec, c1["id"], 1, "Maria Silva")
    criar_aluno(client, sec, c1["id"], 2, "João Souza")
    criar_aluno(client, sec, c2["id"], 3, "Mariana Lopes")

    nomes = lambda r: [a["nome"] for a in r.json()["data"]]  # noqa: E731
    assert nomes(client.get(f"{API}/alunos?nome=MARI", headers=sec)) == ["Maria Silva", "Mariana Lopes"]
    assert len(client.get(f"{API}/alunos?curso_id={c1['id']}", headers=sec).json()["data"]) == 2
    assert client.get(f"{API}/alunos?status=FORMADO", headers=sec).json()["total"] == 0
    assert nomes(client.get(f"{API}/alunos?sort=-nome", headers=sec)) == ["Mariana Lopes", "Maria Silva", "João Souza"]
    assert nomes(client.get(f"{API}/alunos?sort=nome", headers=sec))[0] == "João Souza"

    r = client.get(f"{API}/alunos?sort=senha", headers=sec)
    assert r.status_code == 400 and r.json()["erro"] == "PARAMETRO_INVALIDO"
    assert client.get(f"{API}/alunos?status=XPTO", headers=sec).status_code == 400

    p = criar_professor(client, sec, 1)
    criar_disciplina(client, sec, c1["id"], p["id"], "A1", semestre=1)
    criar_disciplina(client, sec, c1["id"], p["id"], "A2", semestre=2)
    criar_disciplina(client, sec, c2["id"], p["id"], "B1", semestre=2)
    assert client.get(f"{API}/disciplinas?curso_id={c1['id']}&semestre=2", headers=sec).json()["total"] == 1
    assert client.get(f"{API}/disciplinas?professor_id={p['id']}", headers=sec).json()["total"] == 3
    assert len(client.get(f"{API}/professores?titulacao=MESTRE", headers=sec).json()) == 1
    assert client.get(f"{API}/professores?titulacao=DOUTOR", headers=sec).json() == []


# ============ matrículas: regras de negócio ============
def test_matricula_fluxo_e_regras(client, sec, cenario):
    aluno, disc = cenario["aluno"], cenario["disc"]
    r = matricular(client, sec, aluno["id"], disc["id"])
    assert r.status_code == 201
    m = r.json()
    assert m["situacao"] == "CURSANDO" and m["nota_final"] is None and m["frequencia"] is None

    r = matricular(client, sec, aluno["id"], disc["id"])
    assert r.status_code == 409 and r.json()["erro"] == "MATRICULA_DUPLICADA"
    assert matricular(client, sec, aluno["id"], disc["id"], "2027.1").status_code == 201  # outro período pode

    assert client.get(f"{API}/disciplinas/{disc['id']}", headers=sec).json()["vagas_ocupadas"] == 2
    assert matricular(client, sec, 999, disc["id"]).status_code == 404
    assert matricular(client, sec, aluno["id"], 999).status_code == 404
    r = client.post(f"{API}/matriculas", headers=sec,
                    json={"aluno_id": aluno["id"], "disciplina_id": disc["id"], "periodo": "26-2"})
    assert r.status_code == 400

    det = client.get(f"{API}/matriculas/{m['id']}", headers=sec).json()
    assert det["aluno"]["nome"] == "Aluno 1" and det["disciplina"]["codigo"] == "ENG204"


def test_vagas_esgotadas(client, sec):
    curso, prof = criar_curso(client, sec), criar_professor(client, sec)
    disc = criar_disciplina(client, sec, curso["id"], prof["id"], vagas=1)
    a1, a2 = criar_aluno(client, sec, curso["id"], 1), criar_aluno(client, sec, curso["id"], 2)
    assert matricular(client, sec, a1["id"], disc["id"]).status_code == 201
    r = matricular(client, sec, a2["id"], disc["id"])
    assert r.status_code == 409 and r.json()["erro"] == "VAGAS_ESGOTADAS"


def test_aluno_inativo_nao_matricula(client, sec, cenario):
    aluno = cenario["aluno"]
    client.put(f"{API}/alunos/{aluno['id']}", headers=sec, json={
        "nome": "Aluno 1", "email": "aluno1@email.com", "cpf": "00000050001", "data_nascimento": "2003-05-14",
        "curso_id": cenario["curso"]["id"], "status": "INATIVO"})
    r = matricular(client, sec, aluno["id"], cenario["disc"]["id"])
    assert r.status_code == 409 and r.json()["erro"] == "ALUNO_INATIVO"


def test_lancar_notas_aprovacao_e_reprovacao(client, sec, cenario):
    curso, disc = cenario["curso"], cenario["disc"]
    casos = [(8.5, 92.0, "APROVADO"), (6.0, 75.0, "APROVADO"), (5.9, 100.0, "REPROVADO"), (9.0, 74.9, "REPROVADO")]
    for i, (nota, freq, esperado) in enumerate(casos, start=10):
        aluno = criar_aluno(client, sec, curso["id"], i)
        m = matricular(client, sec, aluno["id"], disc["id"]).json()
        r = client.patch(f"{API}/matriculas/{m['id']}/notas", headers=sec, json={"nota_final": nota, "frequencia": freq})
        assert r.status_code == 200, r.text
        assert r.json() == {"id": m["id"], "nota_final": nota, "frequencia": freq, "situacao": esperado}


def test_notas_invalidas_400(client, sec, cenario):
    m = matricular(client, sec, cenario["aluno"]["id"], cenario["disc"]["id"]).json()
    url = f"{API}/matriculas/{m['id']}/notas"
    r = client.patch(url, headers=sec, json={"nota_final": 11, "frequencia": 90})
    assert r.status_code == 400 and r.json()["erro"] == "NOTA_INVALIDA"
    assert r.json()["mensagem"] == "A nota deve estar entre 0 e 10."
    r = client.patch(url, headers=sec, json={"nota_final": -1, "frequencia": 90})
    assert r.json()["erro"] == "NOTA_INVALIDA"
    r = client.patch(url, headers=sec, json={"nota_final": 7, "frequencia": 101})
    assert r.status_code == 400 and r.json()["erro"] == "FREQUENCIA_INVALIDA"
    assert client.patch(url, headers=sec, json={"nota_final": "abc", "frequencia": 90}).json()["erro"] == "DADOS_INVALIDOS"


def test_atualizar_e_cancelar_matricula(client, sec, cenario):
    aluno, disc = cenario["aluno"], cenario["disc"]
    m = matricular(client, sec, aluno["id"], disc["id"]).json()

    r = client.put(f"{API}/matriculas/{m['id']}", headers=sec, json={"periodo": "2026.2", "situacao": "TRANCADA"})
    assert r.status_code == 200 and r.json()["situacao"] == "TRANCADA"
    assert client.get(f"{API}/disciplinas/{disc['id']}", headers=sec).json()["vagas_ocupadas"] == 0
    r = client.patch(f"{API}/matriculas/{m['id']}/notas", headers=sec, json={"nota_final": 7, "frequencia": 80})
    assert r.status_code == 409 and r.json()["erro"] == "MATRICULA_TRANCADA"

    r = client.put(f"{API}/matriculas/{m['id']}", headers=sec, json={"periodo": "2026.2", "situacao": "APROVADO"})
    assert r.status_code == 400 and r.json()["erro"] == "SITUACAO_INVALIDA"

    client.put(f"{API}/matriculas/{m['id']}", headers=sec, json={"periodo": "2026.2", "situacao": "CURSANDO"})
    client.patch(f"{API}/matriculas/{m['id']}/notas", headers=sec, json={"nota_final": 7, "frequencia": 80})
    r = client.delete(f"{API}/matriculas/{m['id']}", headers=sec)  # disciplina encerrada
    assert r.status_code == 409 and r.json()["erro"] == "MATRICULA_ENCERRADA"
    assert client.put(f"{API}/matriculas/{m['id']}", headers=sec,
                      json={"periodo": "2026.2"}).json()["erro"] == "MATRICULA_ENCERRADA"

    m2 = matricular(client, sec, aluno["id"], disc["id"], "2027.1").json()
    assert client.delete(f"{API}/matriculas/{m2['id']}", headers=sec).status_code == 204
    assert client.get(f"{API}/matriculas/{m2['id']}", headers=sec).status_code == 404


def test_listar_matriculas_com_filtros(client, sec, cenario):
    aluno, disc = cenario["aluno"], cenario["disc"]
    matricular(client, sec, aluno["id"], disc["id"], "2026.1")
    matricular(client, sec, aluno["id"], disc["id"], "2026.2")
    r = client.get(f"{API}/matriculas?periodo=2026.2&situacao=CURSANDO", headers=sec).json()
    assert r["total"] == 1 and r["data"][0]["periodo"] == "2026.2"
    assert client.get(f"{API}/matriculas?aluno_id={aluno['id']}", headers=sec).json()["total"] == 2


# ============ autorização por perfil ============
def test_aluno_permissoes(client, sec, cenario):
    h, aluno, disc, curso = cenario["h_aluno"], cenario["aluno"], cenario["disc"], cenario["curso"]
    outro = criar_aluno(client, sec, curso["id"], 2)

    assert client.get(f"{API}/alunos/{aluno['id']}", headers=h).status_code == 200
    assert client.get(f"{API}/alunos/{aluno['id']}/matriculas", headers=h).status_code == 200
    assert client.get(f"{API}/cursos", headers=h).status_code == 200            # catálogo aberto
    assert client.get(f"{API}/disciplinas", headers=h).status_code == 200

    for r in (client.get(f"{API}/alunos/{outro['id']}", headers=h),
              client.get(f"{API}/alunos/{outro['id']}/matriculas", headers=h),
              client.get(f"{API}/alunos", headers=h),
              client.post(f"{API}/cursos", headers=h, json={"nome": "Curso X", "duracao_semestres": 8, "turno": "NOTURNO"}),
              client.delete(f"{API}/cursos/{curso['id']}", headers=h)):
        assert r.status_code == 403 and r.json()["erro"] == "ACESSO_NEGADO"

    r = client.post(f"{API}/disciplinas", headers=h, json={
        "codigo": "X1", "nome": "Disciplina X1", "carga_horaria": 30, "semestre": 1, "vagas": 5,
        "curso_id": curso["id"], "professor_id": cenario["prof"]["id"]})
    assert r.status_code == 403 and r.json()["mensagem"] == "Você não tem permissão para esta operação."

    # matrícula: própria pode, de outro aluno não
    assert matricular(client, h, aluno["id"], disc["id"]).status_code == 201
    assert matricular(client, h, outro["id"], disc["id"]).status_code == 403
    m_outro = matricular(client, sec, outro["id"], disc["id"]).json()
    assert client.get(f"{API}/matriculas/{m_outro['id']}", headers=h).status_code == 403


def test_professor_permissoes(client, sec, cenario):
    h, curso = cenario["h_prof"], cenario["curso"]
    m = matricular(client, sec, cenario["aluno"]["id"], cenario["disc"]["id"]).json()

    assert client.get(f"{API}/alunos", headers=h).status_code == 200            # leitura geral
    assert client.get(f"{API}/professores", headers=h).status_code == 200
    assert client.post(f"{API}/alunos", headers=h, json={}).status_code == 403  # escrita não

    r = client.patch(f"{API}/matriculas/{m['id']}/notas", headers=h, json={"nota_final": 9, "frequencia": 95})
    assert r.status_code == 200 and r.json()["situacao"] == "APROVADO"

    # disciplina de OUTRO professor: negado
    prof2 = criar_professor(client, sec, 2)
    disc2 = criar_disciplina(client, sec, curso["id"], prof2["id"], codigo="ENG999")
    m2 = matricular(client, sec, cenario["aluno"]["id"], disc2["id"]).json()
    r = client.patch(f"{API}/matriculas/{m2['id']}/notas", headers=h, json={"nota_final": 9, "frequencia": 95})
    assert r.status_code == 403 and r.json()["erro"] == "ACESSO_NEGADO"


def test_admin_acessa_tudo(client):
    criar_usuario("admin@faculdade.com.br", "ADMIN")
    h = login(client, "admin@faculdade.com.br")
    assert client.post(f"{API}/cursos", headers=h,
                       json={"nome": "Curso X", "duracao_semestres": 8, "turno": "NOTURNO"}).status_code == 201
    assert client.get(f"{API}/alunos", headers=h).status_code == 200
