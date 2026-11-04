import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from ...tools.regulamento_tools import indice_capitulos, ler_capitulo

load_dotenv()

regulamento_subagent = Agent(
    name="regulamento",
    model=os.environ["MODELO_ESPECIALISTA"],
    description=(
        "Responde dúvidas sobre o regulamento interno do Residencial Aurora (horários, regras de "
        "uso das áreas comuns, silêncio, animais, mudanças, obras, garagem, lixo, penalidades). "
        "Em 'request', passe a pergunta do morador."
    ),
    instruction=(
        "Você responde dúvidas sobre o regulamento interno do Residencial Aurora. "
        "Você não tem o texto do regulamento: ele é consultado por capítulo. "
        "Capítulos disponíveis (use ler_capitulo com o número):\n"
        f"{indice_capitulos()}\n"
        "Escolha pelo título o capítulo que trata do assunto da pergunta e leia só ele; "
        "leia um segundo capítulo apenas se a pergunta realmente depender dele. "
        "Responda somente com base no texto lido, em português do Brasil, de forma resumida "
        "e citando o artigo. Não copie o capítulo. "
        "Se o regulamento não tratar do assunto, diga isso com clareza, sem inventar regras."
    ),
    tools=[ler_capitulo],
)
