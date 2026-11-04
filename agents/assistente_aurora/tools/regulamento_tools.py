import re
from functools import cache
from pathlib import Path

ARQUIVO_REGULAMENTO = Path(__file__).resolve().parents[3] / "dados" / "regulamento.md"
CABECALHO = re.compile(r"^Capítulo\s+([IVXLC]+):\s*(.+)$")
ALGARISMOS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _romano_para_inteiro(romano: str) -> int:
    total = 0
    for atual, proximo in zip(romano, romano[1:] + " "):
        valor = ALGARISMOS[atual]
        total += -valor if ALGARISMOS.get(proximo, 0) > valor else valor
    return total


@cache
def _capitulos() -> dict[int, dict]:
    """Divide o regulamento nos blocos que começam com '## Capítulo'."""
    texto = ARQUIVO_REGULAMENTO.read_text(encoding="utf-8")
    capitulos: dict[int, dict] = {}
    for bloco in re.split(r"(?m)^## ", texto)[1:]:
        correspondencia = CABECALHO.match(bloco.splitlines()[0])
        if not correspondencia:
            continue
        numero = _romano_para_inteiro(correspondencia.group(1))
        capitulos[numero] = {
            "titulo": correspondencia.group(2).strip(),
            "texto": bloco.strip(),
        }
    return capitulos


def indice_capitulos() -> str:
    """Só os números e títulos dos capítulos, sem nenhum texto do regulamento."""
    return "\n".join(
        f"{numero}. {dados['titulo']}" for numero, dados in _capitulos().items()
    )


def ler_capitulo(numero: int) -> dict:
    """Devolve o texto de um único capítulo do regulamento interno do condomínio.

    Use depois de escolher, pelo índice de capítulos, o capítulo que trata do assunto
    da pergunta do morador. Devolve só aquele capítulo.

    Args:
        numero: número do capítulo, de 1 a 14.

    Returns:
        dict: {"status": "ok", "capitulo", "titulo", "texto"} ou
        {"status": "erro", "mensagem": "..."}.
    """
    capitulos = _capitulos()
    dados = capitulos.get(numero) if isinstance(numero, int) else None
    if not dados:
        return {
            "status": "erro",
            "mensagem": f"Capítulo inexistente. Use um número de 1 a {len(capitulos)}.",
        }
    return {
        "status": "ok",
        "capitulo": numero,
        "titulo": dados["titulo"],
        "texto": dados["texto"],
    }
