from app.database import SessionLocal
from app.models import Usuario
from app.security import hash_senha

API = "/api/v1"
SENHA = "123456"
_HASH = hash_senha(SENHA)  # calculado uma vez só (o PBKDF2 é propositalmente lento)


def criar_usuario(email, perfil, aluno_id=None, professor_id=None):
    with SessionLocal() as db:
        db.add(Usuario(email=email, senha_hash=_HASH, perfil=perfil, ativo=True,
                       aluno_id=aluno_id, professor_id=professor_id))
        db.commit()


def login(client, email):
    r = client.post(f"{API}/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def criar_curso(client, h, nome="Engenharia de Software"):
    r = client.post(f"{API}/cursos", json={"nome": nome, "duracao_semestres": 10, "turno": "NOTURNO"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def criar_professor(client, h, n=1):
    r = client.post(f"{API}/professores", headers=h, json={
        "nome": f"Professor {n}", "email": f"prof{n}@faculdade.com.br", "cpf": f"{n:011d}", "titulacao": "MESTRE"})
    assert r.status_code == 201, r.text
    return r.json()


def criar_aluno(client, h, curso_id, n=1, nome=None):
    r = client.post(f"{API}/alunos", headers=h, json={
        "nome": nome or f"Aluno {n}", "email": f"aluno{n}@email.com", "cpf": f"{n + 50000:011d}",
        "data_nascimento": "2003-05-14", "curso_id": curso_id})
    assert r.status_code == 201, r.text
    return r.json()


def criar_disciplina(client, h, curso_id, professor_id, codigo="ENG204", vagas=40, semestre=5):
    r = client.post(f"{API}/disciplinas", headers=h, json={
        "codigo": codigo, "nome": f"Disciplina {codigo}", "carga_horaria": 60, "semestre": semestre,
        "vagas": vagas, "curso_id": curso_id, "professor_id": professor_id})
    assert r.status_code == 201, r.text
    return r.json()


def matricular(client, h, aluno_id, disciplina_id, periodo="2026.2"):
    return client.post(f"{API}/matriculas", headers=h,
                       json={"aluno_id": aluno_id, "disciplina_id": disciplina_id, "periodo": periodo})
