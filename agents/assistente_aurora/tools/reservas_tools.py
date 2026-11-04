import logging
import sqlite3

from google.adk.tools.tool_context import ToolContext

from db import repo

from .validacao import erro_de_area, erro_de_data

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


def verificar_disponibilidade(area: str, data: str) -> dict:
    """Confere se uma área comum está livre numa data.

    Use antes de reservar ou quando o morador perguntar se uma data está livre.
    Só informa livre ou ocupada, nunca de quem é a reserva.

    Args:
        area: id da área: "salao-de-festas", "churrasqueira" ou "quadra".
        data: data no formato AAAA-MM-DD.

    Returns:
        dict: {"status": "ok", "area", "data", "disponivel": true/false} ou
        {"status": "erro", "mensagem": "..."}.
    """
    erro = erro_de_area(area) or erro_de_data(data)
    if erro:
        return erro
    try:
        return {
            "status": "ok",
            "area": area,
            "data": data,
            "disponivel": repo.data_disponivel(area, data),
        }
    except sqlite3.Error:
        logger.exception("Falha ao verificar disponibilidade")
        return {"status": "erro", "mensagem": "Não consegui consultar a agenda agora."}


def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
    """Reserva uma área comum para o apartamento do morador numa data.

    Use quando o morador pedir para reservar. A reserva é sempre do apartamento
    da sessão. Se a área tiver taxa, a reserva gera cobrança e só é gravada depois
    que o morador confirmar; sem taxa, grava direto.

    Args:
        area: id da área: "salao-de-festas", "churrasqueira" ou "quadra".
        data: data no formato AAAA-MM-DD.

    Returns:
        dict: {"status": "reservada", "codigo", "area", "data"},
        {"status": "aguardando_confirmacao"} (nada foi gravado ainda),
        {"status": "nao_reservada", "mensagem": "..."} (o morador negou),
        {"status": "ocupada", "mensagem": "..."} ou
        {"status": "erro", "mensagem": "..."}.
    """
    apartamento = tool_context.state.get("apartamento")
    if not apartamento:
        return {"status": "erro", "mensagem": "Sessão sem apartamento definido."}
    erro = erro_de_area(area) or erro_de_data(data)
    if erro:
        return erro
    try:
        if not repo.data_disponivel(area, data):
            return {
                "status": "ocupada",
                "mensagem": "A área já está reservada nessa data.",
            }
        taxa = repo.obter_area(area)["taxa"]
        if taxa > 0:
            if tool_context.tool_confirmation is None:
                tool_context.request_confirmation(
                    hint=(
                        f"Confirmar a reserva de {area} em {data}? "
                        f"Será gerada uma cobrança de R$ {taxa:.2f}."
                    ),
                    payload={"area": area, "data": data, "taxa": taxa},
                )
                return {"status": "aguardando_confirmacao"}
            if not tool_context.tool_confirmation.confirmed:
                return {
                    "status": "nao_reservada",
                    "mensagem": "Reserva não confirmada pelo morador. Nada foi gravado.",
                }
        resultado = repo.criar_reserva(apartamento, area, data)
    except (sqlite3.Error, RuntimeError):
        logger.exception("Falha ao reservar área")
        return {"status": "erro", "mensagem": "Não consegui gravar a reserva agora."}
    if resultado["status"] == "ocupada":
        return {"status": "ocupada", "mensagem": "A área já está reservada nessa data."}
    return {
        "status": "reservada",
        "codigo": resultado["codigo"],
        "area": area,
        "data": data,
    }


def cancelar_reserva(
    area: str = "", data: str = "", codigo: str = "", tool_context: ToolContext = None
) -> dict:
    """Cancela uma reserva do próprio morador, sem pedir confirmação.

    Informe a área e a data da reserva, ou o código dela. Só reservas do
    apartamento da sessão podem ser canceladas.

    Args:
        area: id da área ("salao-de-festas", "churrasqueira" ou "quadra"). Opcional.
        data: data da reserva, AAAA-MM-DD. Opcional.
        codigo: código da reserva, por exemplo RSV-1377. Opcional.

    Returns:
        dict: {"status": "cancelada", "area", "data"} ou
        {"status": "nao_encontrada", "mensagem": "..."} ou
        {"status": "erro", "mensagem": "..."}.
    """
    apartamento = tool_context.state.get("apartamento")
    if not apartamento:
        return {"status": "erro", "mensagem": "Sessão sem apartamento definido."}
    if not (codigo or (area and data)):
        return {
            "status": "erro",
            "mensagem": "Informe a área e a data, ou o código da reserva.",
        }
    if area:
        erro = erro_de_area(area)
        if erro:
            return erro
    if data:
        erro = erro_de_data(data)
        if erro:
            return erro
    try:
        cancelada = repo.cancelar_reserva(
            apartamento, codigo or None, area or None, data or None
        )
    except sqlite3.Error:
        logger.exception("Falha ao cancelar reserva")
        return {"status": "erro", "mensagem": "Não consegui cancelar a reserva agora."}
    if not cancelada:
        return {
            "status": "nao_encontrada",
            "mensagem": "Não encontrei essa reserva entre as suas.",
        }
    return {"status": "cancelada", "area": area or None, "data": data or None}
