import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./academico.db")

# Em produção, defina SECRET_KEY por variável de ambiente (mín. 32 caracteres).
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-troque-esta-chave-em-producao-0123456789")
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = int(os.getenv("TOKEN_EXPIRE_SECONDS", "7200"))  # 2 horas

# Regras de aprovação
NOTA_MINIMA = 6.0
FREQUENCIA_MINIMA = 75.0
