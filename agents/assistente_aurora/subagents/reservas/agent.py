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
    mode="single_turn",
    description=(
        "Executa tarefas de reservas de áreas comuns (salão de festas, churrasqueira e quadra) "
        "do morador: consultar as reservas dele, ver a agenda e as taxas, reservar e cancelar. "
        "Em 'request', passe o pedido completo, com a área e a data quando houver."
    ),
    instruction=(
        "Você executa tarefas de reservas do Residencial Aurora e devolve o resultado. "
        "Quem conversa com o morador é outro agente: não faça perguntas, só execute. "
        "Use minhas_reservas para as reservas do morador, listar_areas para as áreas e taxas, "
        "verificar_disponibilidade para saber se uma data está livre, reservar_area para reservar "
        "e cancelar_reserva para cancelar uma reserva dele. "
        "As datas das ferramentas usam o formato AAAA-MM-DD: converta datas como 05/11/2026. "
        "Se faltar a área ou a data, devolva dizendo exatamente o que falta. "
        "Quando a ferramenta informar o apartamento, diga de qual apartamento são os dados. "
        "Devolva o resultado em poucas frases, sempre com o status que a ferramenta informou: "
        "reservada, cancelada, ocupada, nao_encontrada, aguardando_confirmacao, nao_reservada ou erro. "
        "Se reservar_area devolver aguardando_confirmacao, informe que a reserva está aguardando "
        "confirmação e que nada foi feito ainda. "
        "Nunca diga que uma ação foi feita antes da confirmação, nem invente detalhes. "
        "Se o pedido não for sobre reservas, devolva dizendo que não é com você."
    ),
    tools=[
        minhas_reservas,
        listar_areas,
        verificar_disponibilidade,
        reservar_area,
        cancelar_reserva,
    ],
)
