import logging
import sqlite3

from google.adk.tools.tool_context import ToolContext

from db import repo

logger = logging.getLogger(__name__)


def meus_visitantes(tool_context: ToolContext) -> dict:
    """Lista os visitantes que o morador que está conversando já autorizou.

    Use quando o morador perguntar quais visitantes ele autorizou. Não recebe
    parâmetros: os visitantes são sempre os do apartamento da sessão.

    Returns:
        dict: {"status": "ok", "apartamento": "<apartamento da sessão>",
        "visitantes": [{"nome", "data"}]} ou {"status": "erro", "mensagem": "..."}.
    """
    apartamento = tool_context.state.get("apartamento")
    if not apartamento:
        return {"status": "erro", "mensagem": "Sessão sem apartamento definido."}
    try:
        return {
            "status": "ok",
            "apartamento": apartamento,
            "visitantes": repo.listar_visitantes(apartamento),
        }
    except sqlite3.Error:
        logger.exception("Falha ao listar visitantes")
        return {
            "status": "erro",
            "mensagem": "Não consegui consultar os visitantes agora.",
        }
