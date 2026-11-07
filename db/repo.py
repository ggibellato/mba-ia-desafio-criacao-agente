import logging
import secrets
import sqlite3
import time

from .engine import conexao

logger = logging.getLogger(__name__)

TENTATIVAS_CODIGO = 5
TENTATIVAS_BLOQUEIO = 5


def listar_reservas(apartamento: str) -> list[dict]:
    """Reservas ativas do apartamento, da mais próxima para a mais distante."""
    with conexao() as conn:
        linhas = conn.execute(
            "SELECT codigo, area, data FROM reservas "
            "WHERE apartamento = ? AND status = 'ativa' ORDER BY data, codigo",
            (apartamento,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def listar_visitantes(apartamento: str) -> list[dict]:
    """Visitantes autorizados pelo apartamento, em ordem de data."""
    with conexao() as conn:
        linhas = conn.execute(
            "SELECT nome, data FROM visitantes WHERE apartamento = ? ORDER BY data, id",
            (apartamento,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def listar_areas() -> list[dict]:
    """Áreas comuns com a taxa de reserva (0 = sem cobrança)."""
    with conexao() as conn:
        linhas = conn.execute("SELECT id, nome, taxa FROM areas ORDER BY id").fetchall()
    return [dict(linha) for linha in linhas]


def obter_area(area_id: str) -> dict | None:
    """A área com o id informado, ou None se não existir."""
    with conexao() as conn:
        linha = conn.execute(
            "SELECT id, nome, taxa FROM areas WHERE id = ?", (area_id,)
        ).fetchone()
    return dict(linha) if linha else None


def data_disponivel(area_id: str, data: str) -> bool:
    """True se não há reserva ativa da área na data. Nunca revela de quem é."""
    with conexao() as conn:
        linha = conn.execute(
            "SELECT 1 FROM reservas WHERE area = ? AND data = ? AND status = 'ativa'",
            (area_id, data),
        ).fetchone()
    return linha is None


def _novo_codigo() -> str:
    return f"RSV-{secrets.token_hex(3).upper()}"


def _inserir_reserva(codigo: str, apartamento: str, area_id: str, data: str) -> None:
    """INSERT da reserva. Se o banco estiver bloqueado, espera um pouco e tenta de novo."""
    for tentativa in range(TENTATIVAS_BLOQUEIO):
        try:
            with conexao() as conn:
                conn.execute(
                    "INSERT INTO reservas (codigo, apartamento, area, data, status) "
                    "VALUES (?, ?, ?, ?, 'ativa')",
                    (codigo, apartamento, area_id, data),
                )
            return
        except sqlite3.OperationalError as erro:
            ultima = tentativa == TENTATIVAS_BLOQUEIO - 1
            if "locked" not in str(erro).lower() or ultima:
                raise
            time.sleep(0.05 * (tentativa + 1))


def criar_reserva(apartamento: str, area_id: str, data: str) -> dict:
    """Grava uma reserva ativa. O código é gerado aqui e nunca repete outro.

    Devolve {"status": "reservada", "codigo": ...} ou {"status": "ocupada"} quando
    a área já tem reserva ativa na data (o índice ux_reserva_ativa decide).
    """
    for _ in range(TENTATIVAS_CODIGO):
        codigo = _novo_codigo()
        try:
            _inserir_reserva(codigo, apartamento, area_id, data)
        except sqlite3.IntegrityError as erro:
            if "reservas.codigo" in str(erro):
                continue
            if "reservas.area" in str(erro):
                logger.info(
                    "Índice ux_reserva_ativa recusou a gravação: %s já reservada em %s",
                    area_id,
                    data,
                )
                return {"status": "ocupada"}
            raise
        return {"status": "reservada", "codigo": codigo}
    raise RuntimeError("Não foi possível gerar um código de reserva único.")


def cancelar_reserva(
    apartamento: str,
    codigo: str | None = None,
    area_id: str | None = None,
    data: str | None = None,
) -> str | None:
    """Cancela (soft delete) uma reserva ativa do apartamento.

    Todos os critérios informados precisam casar, e o apartamento sempre entra no
    filtro. Devolve o código cancelado ou None se nada casar, sem distinguir
    "não existe" de "é de outro apartamento".
    """
    criterios = {"codigo": codigo, "area": area_id, "data": data}
    filtros = {campo: valor for campo, valor in criterios.items() if valor}
    if not filtros:
        return None
    condicoes = " AND ".join(f"{campo} = ?" for campo in filtros)
    with conexao() as conn:
        linha = conn.execute(
            "UPDATE reservas SET status = 'cancelada' "
            f"WHERE apartamento = ? AND status = 'ativa' AND {condicoes} "
            "RETURNING codigo",
            (apartamento, *filtros.values()),
        ).fetchone()
    return linha["codigo"] if linha else None


def autorizar_visitante(apartamento: str, nome: str, data: str) -> dict:
    """Registra a autorização de entrada de um visitante para a data."""
    with conexao() as conn:
        conn.execute(
            "INSERT INTO visitantes (apartamento, nome, data) VALUES (?, ?, ?)",
            (apartamento, nome, data),
        )
    return {"nome": nome, "data": data}


def registrar_sessao(session_id: str, apartamento: str) -> None:
    """Liga a sessão do ADK ao apartamento dela (definido na criação da sessão)."""
    with conexao() as conn:
        conn.execute(
            "INSERT INTO sessoes_apartamento (session_id, apartamento) VALUES (?, ?)",
            (session_id, apartamento),
        )


def apartamento_da_sessao(session_id: str) -> str | None:
    """O apartamento da sessão, ou None se a sessão não existe."""
    with conexao() as conn:
        linha = conn.execute(
            "SELECT apartamento FROM sessoes_apartamento WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return linha["apartamento"] if linha else None
