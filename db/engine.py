import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = RAIZ / ".dados" / "condominio.db"

TABELAS_DE_DADOS = ("visitantes", "reservas", "areas", "apartamentos")

SCHEMA = """
CREATE TABLE IF NOT EXISTS apartamentos (
    numero TEXT PRIMARY KEY,
    morador TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS areas (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    taxa REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS reservas (
    codigo TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL,
    area TEXT NOT NULL REFERENCES areas(id),
    data TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ativa'
);
-- Garantia 5: exclusividade no instante da gravação
CREATE UNIQUE INDEX IF NOT EXISTS ux_reserva_ativa
    ON reservas(area, data) WHERE status = 'ativa';
CREATE TABLE IF NOT EXISTS visitantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartamento TEXT NOT NULL,
    nome TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessoes_apartamento (
    session_id TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL
);
"""


@contextmanager
def conexao() -> Iterator[sqlite3.Connection]:
    """Abre uma conexão, confirma ao sair sem erro e sempre fecha."""
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def criar_schema() -> None:
    """Cria as tabelas e o índice que faltarem (idempotente, não apaga dados)."""
    with conexao() as conn:
        conn.executescript(SCHEMA)
