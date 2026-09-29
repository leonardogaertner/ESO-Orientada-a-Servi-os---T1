"""Padrão único de erro da API:

{
  "status": 404,
  "erro": "RECURSO_NAO_ENCONTRADO",
  "mensagem": "Aluno não encontrado.",
  "caminho": "/api/v1/alunos/999",
  "timestamp": "2026-09-29T14:30:00Z"
}
"""
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("academico")


class AppError(Exception):
    def __init__(self, status: int, erro: str, mensagem: str, detalhes: list[dict] | None = None):
        self.status = status
        self.erro = erro
        self.mensagem = mensagem
        self.detalhes = detalhes


def _resposta(request: Request, status: int, erro: str, mensagem: str, detalhes=None) -> JSONResponse:
    corpo = {
        "status": status,
        "erro": erro,
        "mensagem": mensagem,
        "caminho": request.url.path,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if detalhes:
        corpo["detalhes"] = detalhes
    return JSONResponse(status_code=status, content=corpo)


def _traduzir(err: dict) -> str:
    tipo, ctx = err["type"], err.get("ctx", {})
    if tipo == "missing":
        return "Campo obrigatório."
    if tipo == "value_error":
        return err["msg"].removeprefix("Value error, ")
    if tipo == "enum":
        return f"Valor inválido. Valores permitidos: {ctx.get('expected')}."
    if tipo in ("int_parsing", "int_type", "float_parsing", "float_type"):
        return "Deve ser um número."
    if tipo == "string_type":
        return "Deve ser um texto."
    if tipo in ("date_parsing", "date_type", "date_from_datetime_parsing"):
        return "Data inválida. Use o formato AAAA-MM-DD."
    if tipo == "greater_than_equal":
        return f"Deve ser maior ou igual a {ctx.get('ge')}."
    if tipo == "less_than_equal":
        return f"Deve ser menor ou igual a {ctx.get('le')}."
    if tipo == "string_too_short":
        return f"Deve ter no mínimo {ctx.get('min_length')} caracteres."
    if tipo == "string_too_long":
        return f"Deve ter no máximo {ctx.get('max_length')} caracteres."
    return err["msg"]


def _campo(loc) -> str:
    partes = [str(p) for p in loc if p not in ("body", "query", "path")]
    if not partes or all(p.isdigit() for p in partes):
        return "corpo"
    return ".".join(partes)


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _resposta(request, exc.status, exc.erro, exc.mensagem, exc.detalhes)

    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError):
        detalhes = []
        for err in exc.errors():
            if err["type"] == "json_invalid":
                detalhes.append({"campo": "corpo", "problema": "JSON inválido."})
            else:
                detalhes.append({"campo": _campo(err["loc"]), "problema": _traduzir(err)})
        return _resposta(request, 400, "DADOS_INVALIDOS", "Um ou mais campos são inválidos.", detalhes)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return _resposta(request, 404, "RECURSO_NAO_ENCONTRADO", "Recurso não encontrado.")
        if exc.status_code == 405:
            return _resposta(request, 405, "METODO_NAO_PERMITIDO", "Método HTTP não permitido para este recurso.")
        return _resposta(request, exc.status_code, "ERRO_HTTP", str(exc.detail))

    @app.exception_handler(IntegrityError)
    async def _integridade(request: Request, exc: IntegrityError):
        # Rede de segurança para corridas (ex.: dois cadastros simultâneos com o mesmo CPF).
        log.warning("IntegrityError em %s: %s", request.url.path, exc.orig)
        return _resposta(request, 409, "CONFLITO_DE_DADOS", "A operação viola uma restrição de integridade dos dados.")

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception):
        log.exception("Erro não tratado em %s", request.url.path)
        return _resposta(request, 500, "ERRO_INTERNO", "Erro interno. Tente novamente mais tarde.")
