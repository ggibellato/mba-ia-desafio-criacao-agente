import os

from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()

root_agent = Agent(
    name="assistente_aurora",
    model=os.environ["MODELO_PRINCIPAL"],
    description="Assistente virtual do Residencial Aurora.",
    instruction=(
        "Você é o assistente virtual do Residencial Aurora, no aplicativo dos moradores. "
        "Responda sempre em português do Brasil, de forma cordial e objetiva."
    ),
)
