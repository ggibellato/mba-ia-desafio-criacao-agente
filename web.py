"""API do assistente virtual do Residencial Aurora.

Rodar (da raiz do repositório):

    uv run uvicorn web:app --port 8000

Sessão -> App -> Runner -> API. As sessões ficam em SQLite (.adk/sessoes.db) e, por isso,
sobrevivem ao reinício. Os dados do condomínio ficam em .dados/condominio.db; a API só cria
o schema se faltar e nunca restaura os dados (isso é o `python -m db.reset`).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from google.adk import Runner
from google.adk.events import Event
from google.adk.sessions import Session
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types
from pydantic import BaseModel, Field

from agents.assistente_aurora.agent import app as aurora_app
from db import repo
from db.engine import criar_schema

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent
BANCO_SESSOES = RAIZ / ".adk" / "sessoes.db"
NOME_DO_APP = aurora_app.name

BANCO_SESSOES.parent.mkdir(parents=True, exist_ok=True)
session_service = SqliteSessionService(str(BANCO_SESSOES))
runner = Runner(app=aurora_app, session_service=session_service)


@asynccontextmanager
async def lifespan(_: FastAPI):
    criar_schema()
    yield


app = FastAPI(title="Assistente do Residencial Aurora", lifespan=lifespan)


# --------------------------------------------------------------------------- #
# Modelos                                                                      #
# --------------------------------------------------------------------------- #


class NovaSessao(BaseModel):
    apartamento: str = Field(
        min_length=1, description="Apartamento do morador autenticado."
    )


class SessaoCriada(BaseModel):
    session_id: str


class NovaMensagem(BaseModel):
    texto: str


class ConfirmacaoPendente(BaseModel):
    id: str
    acao: str
    detalhes: dict


class RespostaMensagem(BaseModel):
    resposta: str
    confirmacoes_pendentes: list[ConfirmacaoPendente]


class ReservaVerificacao(BaseModel):
    codigo: str
    area: str
    data: str


class VisitanteVerificacao(BaseModel):
    nome: str
    data: str


# --------------------------------------------------------------------------- #
# Auxiliares                                                                   #
# --------------------------------------------------------------------------- #


async def _buscar_sessao(session_id: str) -> Session:
    """A sessão do ADK, ou 404. O apartamento vem da tabela, não do cliente."""
    apartamento = repo.apartamento_da_sessao(session_id)
    sessao = None
    if apartamento:
        sessao = await session_service.get_session(
            app_name=NOME_DO_APP, user_id=apartamento, session_id=session_id
        )
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return sessao


def _texto(evento: Event) -> str | None:
    if not evento.content or not evento.content.parts:
        return None
    partes = [parte.text for parte in evento.content.parts if parte.text]
    return "\n".join(partes) if partes else None


# --------------------------------------------------------------------------- #
# Rotas de conversa                                                            #
# --------------------------------------------------------------------------- #


@app.post("/sessoes", status_code=201, response_model=SessaoCriada)
async def criar_sessao(pedido: NovaSessao) -> SessaoCriada:
    apartamento = pedido.apartamento.strip()
    if not apartamento:
        raise HTTPException(status_code=422, detail="Informe o apartamento.")
    sessao = await session_service.create_session(
        app_name=NOME_DO_APP,
        user_id=apartamento,
        state={"apartamento": apartamento},
    )
    repo.registrar_sessao(sessao.id, apartamento)
    logger.info("Sessão criada: %s", sessao.id)
    return SessaoCriada(session_id=sessao.id)


@app.post("/sessoes/{session_id}/mensagens", response_model=RespostaMensagem)
async def enviar_mensagem(session_id: str, pedido: NovaMensagem) -> RespostaMensagem:
    sessao = await _buscar_sessao(session_id)
    conteudo = types.Content(
        role="user", parts=[types.Part.from_text(text=pedido.texto)]
    )

    resposta = ""
    async for evento in runner.run_async(
        user_id=sessao.user_id, session_id=sessao.id, new_message=conteudo
    ):
        if evento.author == aurora_app.root_agent.name and evento.is_final_response():
            resposta = _texto(evento) or resposta
    return RespostaMensagem(resposta=resposta, confirmacoes_pendentes=[])


@app.get("/sessoes/{session_id}/eventos")
async def listar_eventos(session_id: str) -> list[dict]:
    sessao = await _buscar_sessao(session_id)
    return [
        evento.model_dump(mode="json", exclude_none=True) for evento in sessao.events
    ]


# --------------------------------------------------------------------------- #
# Rotas de verificação (leem o banco direto, sem passar pelo modelo)           #
# --------------------------------------------------------------------------- #


@app.get("/apartamentos/{numero}/reservas", response_model=list[ReservaVerificacao])
async def reservas_do_apartamento(numero: str) -> list[dict]:
    return repo.listar_reservas(numero)


@app.get("/apartamentos/{numero}/visitantes", response_model=list[VisitanteVerificacao])
async def visitantes_do_apartamento(numero: str) -> list[dict]:
    return repo.listar_visitantes(numero)
