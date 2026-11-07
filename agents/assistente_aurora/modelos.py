import os

from google.adk.models.google_llm import Gemini
from google.genai import types

# Erros de cota e de rede (429, 5xx) são tratados no cliente HTTP do modelo, com espera
# crescente entre as tentativas. Os nomes dos modelos vêm do .env, nunca do código.
OPCOES_DE_RETRY = types.HttpRetryOptions(
    attempts=5, initial_delay=2.0, max_delay=30.0, exp_base=2.0
)


def criar_modelo(variavel_de_ambiente: str) -> Gemini:
    """Gemini cujo nome vem da variável de ambiente informada, com retry de cota e rede."""
    return Gemini(model=os.environ[variavel_de_ambiente], retry_options=OPCOES_DE_RETRY)
