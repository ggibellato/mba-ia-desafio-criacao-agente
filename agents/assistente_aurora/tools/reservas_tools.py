import logging
import sqlite3

from google.adk.tools.tool_context import ToolContext

from db import repo

logger = logging.getLogger(__name__)


def minhas_reservas(tool_context: ToolContext) -> dict:
    """Lista as reservas ativas do morador que está conversando.

    Use quando o morador perguntar quais são as suas reservas. Não recebe
    parâmetros: as reservas são sempre as do apartamento da sessão.

    Returns:
        dict: {"status": "ok", "apartamento": "<apartamento da sessão>",
        "reservas": [{"codigo", "area", "data"}]} ou
        {"status": "erro", "mensagem": "..."}.
    """
    apartamento = tool_context.state.get("apartamento")
    if not apartamento:
        return {"status": "erro", "mensagem": "Sessão sem apartamento definido."}
    try:
        return {
            "status": "ok",
            "apartamento": apartamento,
            "reservas": repo.listar_reservas(apartamento),
        }
    except sqlite3.Error:
        logger.exception("Falha ao listar reservas")
        return {
            "status": "erro",
            "mensagem": "Não consegui consultar as reservas agora.",
        }


def listar_areas() -> dict:
    """Lista as áreas comuns que podem ser reservadas, com a taxa de cada uma.

    Use quando o morador perguntar quais áreas existem ou quanto custa reservar.
    Taxa 0 significa que a reserva não gera cobrança.

    Returns:
        dict: {"status": "ok", "areas": [{"id", "nome", "taxa"}]} ou
        {"status": "erro", "mensagem": "..."}.
    """
    try:
        return {"status": "ok", "areas": repo.listar_areas()}
    except sqlite3.Error:
        logger.exception("Falha ao listar áreas")
        return {"status": "erro", "mensagem": "Não consegui consultar as áreas agora."}
