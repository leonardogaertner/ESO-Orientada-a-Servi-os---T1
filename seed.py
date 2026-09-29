"""Cria as tabelas e popula dados de demonstração (idempotente). Uso: python seed.py"""
from datetime import date

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Aluno, Curso, Disciplina, Professor, Usuario
from app.security import hash_senha


def obter_ou_criar(db, model, filtro: dict, valores: dict):
    obj = db.scalar(select(model).filter_by(**filtro))
    if obj is None:
        obj = model(**filtro, **valores)
        db.add(obj)
        db.flush()
    return obj


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        curso = obter_ou_criar(db, Curso, {"nome": "Engenharia de Software"},
                               {"duracao_semestres": 10, "turno": "NOTURNO"})
        prof = obter_ou_criar(db, Professor, {"cpf": "12345678901"},
                              {"nome": "Tiago Souza", "email": "tiago.souza@faculdade.com.br", "titulacao": "MESTRE"})
        obter_ou_criar(db, Disciplina, {"codigo": "ENG204"},
                       {"nome": "APIs, HTTP, JSON e REST", "carga_horaria": 60, "semestre": 5, "vagas": 40,
                        "curso_id": curso.id, "professor_id": prof.id})
        aluno = obter_ou_criar(db, Aluno, {"cpf": "98765432100"},
                               {"matricula": f"{date.today().year}001", "nome": "Maria Oliveira",
                                "email": "maria@email.com", "data_nascimento": date(2003, 5, 14),
                                "status": "ATIVO", "curso_id": curso.id})
        usuarios = [
            ("admin@faculdade.com.br", "admin123", "ADMIN", None, None),
            ("secretaria@faculdade.com.br", "123456", "SECRETARIA", None, None),
            ("professor@faculdade.com.br", "123456", "PROFESSOR", None, prof.id),
            ("aluno@faculdade.com.br", "123456", "ALUNO", aluno.id, None),
        ]
        for email, senha, perfil, aluno_id, professor_id in usuarios:
            obter_ou_criar(db, Usuario, {"email": email},
                           {"senha_hash": hash_senha(senha), "perfil": perfil, "ativo": True,
                            "aluno_id": aluno_id, "professor_id": professor_id})
        db.commit()
    print("Banco pronto. Usuários de demonstração (apenas desenvolvimento!):")
    for email, senha, perfil, *_ in usuarios:
        print(f"  {perfil:<11} {email:<32} senha: {senha}")


if __name__ == "__main__":
    main()
