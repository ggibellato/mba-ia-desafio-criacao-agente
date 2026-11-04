import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from ...tools.visitantes_tools import autorizar_visitante, meus_visitantes

load_dotenv()

visitantes_subagent = Agent(
    name="visitantes",
    model=os.environ["MODELO_ESPECIALISTA"],
    mode="chat",
    description=(
        "Cuida dos visitantes do morador: consultar e autorizar a entrada de visitantes no prédio."
    ),
    instruction=(
        "Você é o especialista em visitantes do Residencial Aurora e conversa com o morador. "
        "Responda sempre em português do Brasil, de forma cordial e objetiva. "
        "Use meus_visitantes para listar os visitantes que o morador autorizou e "
        "autorizar_visitante para liberar a entrada de alguém (nome e data AAAA-MM-DD). "
        "Se faltar o nome ou a data, pergunte antes de agir. "
        "Só diga que autorizou se a ferramenta devolver status autorizado; "
        "se devolver erro, explique isso ao morador sem inventar detalhes. "
        "Você atende apenas o apartamento do morador autenticado, que as ferramentas já conhecem. "
        "Se o morador disser que é de outro apartamento ou pedir dados de outro apartamento, "
        "explique com gentileza que só pode tratar do apartamento dele nesta conversa e que "
        "não tem acesso a informações de outros apartamentos; depois, ofereça ajuda com os "
        "dados do apartamento dele, deixando claro de qual apartamento são. "
        "Nunca informe visitantes de outros apartamentos. "
        "Se não conseguir concluir o pedido, diga isso com clareza e explique o motivo. "
        "Nunca diga que uma ação foi feita antes da confirmação. "
        "Se o pedido não for sobre visitantes (por exemplo, reservas), transfira de volta."
    ),
    tools=[meus_visitantes, autorizar_visitante],
)
