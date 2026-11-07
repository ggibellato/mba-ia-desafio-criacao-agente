from dotenv import load_dotenv
from google.adk.agents import Agent

from ...callbacks import tratar_erro_de_tool
from ...modelos import criar_modelo
from ...tools.visitantes_tools import autorizar_visitante, meus_visitantes

load_dotenv()

visitantes_subagent = Agent(
    name="visitantes",
    model=criar_modelo("MODELO_ESPECIALISTA"),
    on_tool_error_callback=tratar_erro_de_tool,
    mode="single_turn",
    description=(
        "Executa tarefas de visitantes do morador: consultar quem ele já autorizou e liberar "
        "a entrada de alguém no prédio. "
        "Em 'request', passe o pedido completo, com o nome e a data da visita quando houver."
    ),
    instruction=(
        "Você executa tarefas de visitantes do Residencial Aurora e devolve o resultado. "
        "Quem conversa com o morador é outro agente: não faça perguntas, só execute. "
        "Use meus_visitantes para listar os visitantes que o morador autorizou e "
        "autorizar_visitante para liberar a entrada de alguém. "
        "As datas das ferramentas usam o formato AAAA-MM-DD: converta datas como 05/11/2026. "
        "Se faltar o nome ou a data, devolva dizendo exatamente o que falta. "
        "Quando a ferramenta informar o apartamento, diga de qual apartamento são os dados. "
        "Devolva o resultado em poucas frases, sempre com o status que a ferramenta informou: "
        "autorizado, aguardando_confirmacao, nao_autorizado ou erro. "
        "Se autorizar_visitante devolver aguardando_confirmacao, informe que a autorização está "
        "aguardando confirmação e que nada foi feito ainda. "
        "Nunca diga que uma ação foi feita antes da confirmação, nem invente detalhes. "
        "Se o pedido não for sobre visitantes, devolva dizendo que não é com você."
    ),
    tools=[meus_visitantes, autorizar_visitante],
)
