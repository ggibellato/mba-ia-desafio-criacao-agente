import logging

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins import BasePlugin
from google.genai import types

logger = logging.getLogger(__name__)

ERROS_COM_RETRY = {"MALFORMED_RESPONSE", "MALFORMED_FUNCTION_CALL"}
MAXIMO_DE_TENTATIVAS = 3

LEMBRETE = types.Content(
    role="user",
    parts=[
        types.Part(
            text=(
                "Sua resposta anterior não teve conteúdo utilizável. "
                "Tente novamente e forneça uma resposta clara."
            )
        )
    ],
)
DESCULPA = LlmResponse(
    content=types.Content(
        role="model",
        parts=[
            types.Part(
                text=(
                    "Tive um problema técnico ao concluir esta etapa. "
                    "Pode reenviar sua mensagem, por favor?"
                )
            )
        ],
    )
)


def resposta_vazia(resposta: LlmResponse) -> bool:
    """A chamada terminou sem erro, mas sem nenhum conteúdo útil."""
    if resposta.partial or resposta.error_code:
        return False
    for parte in (
        resposta.content.parts if resposta.content and resposta.content.parts else []
    ):
        if parte.thought:
            continue
        if parte.text or parte.function_call or parte.function_response:
            return False
    return True


class ModelRetryPlugin(BasePlugin):
    """Repete a chamada ao modelo quando a resposta vem vazia ou malformada.

    A requisição é guardada por (invocação, agente): os especialistas podem rodar em
    paralelo dentro da mesma invocação e não podem trocar de requisição entre si.
    """

    def __init__(self, name: str = "model_retry_plugin"):
        super().__init__(name=name)
        self._requisicoes: dict[tuple[str, str], LlmRequest] = {}

    @staticmethod
    def _chave(contexto: CallbackContext) -> tuple[str, str]:
        return contexto.invocation_id, contexto.agent_name

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        self._requisicoes[self._chave(callback_context)] = llm_request
        return None

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        requisicao = self._requisicoes.pop(self._chave(callback_context), None)
        codigo = getattr(llm_response.error_code, "name", llm_response.error_code)
        com_defeito = codigo in ERROS_COM_RETRY or resposta_vazia(llm_response)
        if not com_defeito or requisicao is None:
            return None

        nova = requisicao.model_copy(deep=True)
        nova.contents = [*(nova.contents or []), LEMBRETE]
        modelo = callback_context.get_invocation_context().agent.canonical_model
        for tentativa in range(1, MAXIMO_DE_TENTATIVAS + 1):
            logger.warning(
                "Agente %s: resposta %s do modelo; tentativa %d/%d",
                callback_context.agent_name,
                codigo or "vazia",
                tentativa,
                MAXIMO_DE_TENTATIVAS,
            )
            ultima = None
            async for resposta in modelo.generate_content_async(nova, stream=False):
                ultima = resposta
            if ultima and not ultima.error_code and not resposta_vazia(ultima):
                return ultima
        return DESCULPA.model_copy(deep=True)

    async def after_agent_callback(self, *, agent, callback_context: CallbackContext):
        self._requisicoes.pop(self._chave(callback_context), None)
