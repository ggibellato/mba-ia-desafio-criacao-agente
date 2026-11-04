import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from ...tools.reservas_tools import (
    cancelar_reserva,
    listar_areas,
    minhas_reservas,
    reservar_area,
    verificar_disponibilidade,
)

load_dotenv()

reservas_subagent = Agent(
    name="reservas",
    model=os.environ["MODELO_ESPECIALISTA"],
    mode="chat",
    description=(
        "Cuida das reservas de áreas comuns (salão de festas, churrasqueira e quadra) "
        "do morador: consultar, reservar e cancelar reservas, ver a agenda e as taxas."
    ),
    instruction=(
        "Você é o especialista em reservas do Residencial Aurora e conversa com o morador. "
        "Responda sempre em português do Brasil, de forma cordial e objetiva. "
        "Use minhas_reservas para as reservas do morador, listar_areas para as áreas e taxas, "
        "verificar_disponibilidade para saber se uma data está livre, reservar_area para reservar "
        "e cancelar_reserva para cancelar uma reserva dele (o cancelamento não pede confirmação). "
        "As datas usam o formato AAAA-MM-DD. Se faltar a área ou a data, pergunte antes de agir. "
        "Só diga que reservou ou cancelou se a ferramenta devolver status reservada ou cancelada; "
        "se devolver ocupada, nao_encontrada ou erro, explique isso ao morador sem inventar detalhes. "
        "Você atende apenas o apartamento do morador autenticado, que as ferramentas já conhecem. "
        "Se o morador disser que é de outro apartamento ou pedir dados de outro apartamento, "
        "explique com gentileza que só pode tratar do apartamento dele nesta conversa e que "
        "não tem acesso a informações de outros apartamentos; depois, ofereça ajuda com os "
        "dados do apartamento dele, deixando claro de qual apartamento são. "
        "Nunca informe reservas de outros apartamentos. "
        "Se não conseguir concluir o pedido, diga isso com clareza e explique o motivo. "
        "Nunca diga que uma ação foi feita antes da confirmação. "
        "Se o pedido não for sobre reservas (por exemplo, visitantes), transfira de volta."
    ),
    tools=[
        minhas_reservas,
        listar_areas,
        verificar_disponibilidade,
        reservar_area,
        cancelar_reserva,
    ],
)
