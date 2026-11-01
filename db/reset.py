import json
from pathlib import Path

from .engine import RAIZ, TABELAS_DE_DADOS, conexao, criar_schema

PASTA_DADOS = RAIZ / "dados"


def _ler_json(nome: str) -> list[dict]:
    caminho: Path = PASTA_DADOS / nome
    return json.loads(caminho.read_text(encoding="utf-8"))


def restaurar() -> None:
    """Volta apartamentos, áreas, reservas e visitantes ao estado de dados/*.json.

    Não mexe em sessoes_apartamento: as sessões do ADK sobrevivem ao reset.
    """
    with conexao() as conn:
        for tabela in TABELAS_DE_DADOS:
            conn.execute(f"DROP TABLE IF EXISTS {tabela}")
    criar_schema()

    with conexao() as conn:
        conn.executemany(
            "INSERT INTO apartamentos (numero, morador) VALUES (:numero, :morador)",
            _ler_json("apartamentos.json"),
        )
        conn.executemany(
            "INSERT INTO areas (id, nome, taxa) VALUES (:id, :nome, :taxa)",
            _ler_json("areas.json"),
        )
        conn.executemany(
            "INSERT INTO reservas (codigo, apartamento, area, data, status) "
            "VALUES (:codigo, :apartamento, :area, :data, 'ativa')",
            _ler_json("reservas.json"),
        )
        conn.executemany(
            "INSERT INTO visitantes (apartamento, nome, data) "
            "VALUES (:apartamento, :nome, :data)",
            _ler_json("visitantes.json"),
        )


if __name__ == "__main__":
    restaurar()
    print("Dados restaurados.")
