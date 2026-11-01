from .engine import conexao


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
