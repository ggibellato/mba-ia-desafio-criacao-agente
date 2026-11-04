import re
from datetime import date

from db import repo

FORMATO_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def erro_de_data(data: str) -> dict | None:
    """Devolve um erro estruturado se a data não for uma AAAA-MM-DD real."""
    try:
        if FORMATO_DATA.match(data or ""):
            date.fromisoformat(data)
            return None
    except ValueError:
        pass
    return {
        "status": "erro",
        "mensagem": "Data inválida. Use o formato AAAA-MM-DD, por exemplo 2030-04-20.",
    }


def erro_de_area(area_id: str) -> dict | None:
    """Devolve um erro estruturado se a área não existir."""
    if repo.obter_area(area_id):
        return None
    validas = ", ".join(area["id"] for area in repo.listar_areas())
    return {
        "status": "erro",
        "mensagem": f"Área inválida. Use um destes ids: {validas}.",
    }
