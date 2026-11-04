import logging
import sqlite3

from google.adk.tools.tool_context import ToolContext

from db import repo

from .validacao import erro_de_data

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


def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
    """Autoriza a entrada de um visitante no prédio numa data.

    Use quando o morador pedir para liberar a entrada de alguém. A autorização é
    sempre do apartamento da sessão e libera acesso ao prédio, então só é gravada
    depois que o morador confirmar.

    Args:
        nome: nome completo do visitante.
        data: data da visita, no formato AAAA-MM-DD.

    Returns:
        dict: {"status": "autorizado", "nome", "data"},
        {"status": "aguardando_confirmacao"} (nada foi gravado ainda),
        {"status": "nao_autorizado", "mensagem": "..."} (o morador negou) ou
        {"status": "erro", "mensagem": "..."}.
    """
    apartamento = tool_context.state.get("apartamento")
    if not apartamento:
        return {"status": "erro", "mensagem": "Sessão sem apartamento definido."}
    nome = (nome or "").strip()
    if not nome:
        return {"status": "erro", "mensagem": "Informe o nome do visitante."}
    erro = erro_de_data(data)
    if erro:
        return erro
    if tool_context.tool_confirmation is None:
        tool_context.request_confirmation(
            hint=f"Confirmar a liberação da entrada de {nome} em {data}?",
            payload={"nome": nome, "data": data},
        )
        return {"status": "aguardando_confirmacao"}
    if not tool_context.tool_confirmation.confirmed:
        return {
            "status": "nao_autorizado",
            "mensagem": "Autorização não confirmada pelo morador. Nada foi gravado.",
        }
    try:
        repo.autorizar_visitante(apartamento, nome, data)
    except sqlite3.Error:
        logger.exception("Falha ao autorizar visitante")
        return {
            "status": "erro",
            "mensagem": "Não consegui registrar o visitante agora.",
        }
    return {"status": "autorizado", "nome": nome, "data": data}
