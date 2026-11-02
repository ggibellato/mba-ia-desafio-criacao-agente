import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from .subagents.reservas.agent import reservas_subagent
from .subagents.visitantes.agent import visitantes_subagent

load_dotenv()

root_agent = Agent(
    name="assistente_aurora",
    model=os.environ["MODELO_PRINCIPAL"],
    description="Assistente virtual do Residencial Aurora.",
    instruction=(
        "Você é o assistente virtual do Residencial Aurora, no aplicativo dos moradores. "
        "Responda sempre em português do Brasil, de forma cordial e objetiva. "
        "Você só encaminha o morador ao especialista certo: reservas para áreas comuns, "
        "visitantes para quem entra no prédio. "
        "Nunca informe dados de outros apartamentos: cada conversa pertence a um só apartamento."
    ),
    sub_agents=[reservas_subagent, visitantes_subagent],
)
