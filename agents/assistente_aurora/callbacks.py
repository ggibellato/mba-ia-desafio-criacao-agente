import logging
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def tratar_erro_de_tool(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, error: Exception
) -> dict:
    """Uma exceção que escapou da tool vira um resultado estruturado para o modelo.

    O modelo nunca vê o traceback nem a mensagem da exceção. O log guarda só o nome da tool
    e o tipo do erro, sem os argumentos (podem ter nome de visitante).
    """
    logger.error(
        "Erro ao executar a ferramenta %s: %s", tool.name, type(error).__name__
    )
    return {
        "status": "erro",
        "mensagem": "Ocorreu um erro inesperado ao processar o pedido. Nada foi alterado.",
    }
