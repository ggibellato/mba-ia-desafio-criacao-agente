import secrets
import sqlite3

from .engine import conexao

TENTATIVAS_CODIGO = 5


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


def criar_reserva(apartamento: str, area_id: str, data: str) -> dict:
    """Grava uma reserva ativa. O código é gerado aqui e nunca repete outro.

    Devolve {"status": "reservada", "codigo": ...} ou {"status": "ocupada"} quando
    a área já tem reserva ativa na data (o índice ux_reserva_ativa decide).
    """
    for _ in range(TENTATIVAS_CODIGO):
        codigo = _novo_codigo()
        try:
            with conexao() as conn:
                conn.execute(
                    "INSERT INTO reservas (codigo, apartamento, area, data, status) "
                    "VALUES (?, ?, ?, ?, 'ativa')",
                    (codigo, apartamento, area_id, data),
                )
        except sqlite3.IntegrityError as erro:
            if "reservas.codigo" in str(erro):
                continue
            if "reservas.area" in str(erro):
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
