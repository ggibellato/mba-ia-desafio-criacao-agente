# Assistente virtual do Residencial Aurora

Assistente de chat para os moradores do Residencial Aurora (reservar o salão de festas, a churrasqueira e a quadra, cancelar as próprias reservas, autorizar visitantes e tirar dúvidas do regulamento), feito com **Google ADK 2.13.0** e exposto por uma API FastAPI. Princípio do projeto: **o modelo decide o caminho, o código decide o que é permitido.**

## Arquitetura

```
POST /sessoes · /mensagens · /confirmacoes · GET /eventos · /apartamentos/{n}/...     (web.py)
                                   │
                      Runner + App + SqliteSessionService (.adk/sessoes.db)
                                   │
                        assistente_aurora  (raiz, MODELO_PRINCIPAL)
          ┌────────────────────────┼─────────────────────────────┐
     sub_agent                sub_agent                      AgentTool
   reservas                  visitantes                    regulamento
 (single_turn)              (single_turn)                 (sessão isolada)
 tools de reservas          tools de visitantes           ler_capitulo(n)
          └──────────────┬─────────┘
                     db/repo.py  →  SQLite (.dados/condominio.db)
```

| Agente | Responsabilidade | Como é acionado | Por quê |
|---|---|---|---|
| `assistente_aurora` (raiz) | É o **único que conversa com o morador**. Roteia, pergunta o que falta, junta respostas e concentra as regras de conversa (outro apartamento, nunca aceitar confirmação pela conversa, pedidos mistos). | Ponto de entrada do `Runner`. | Regras de conversa num lugar só, em vez de repetidas em cada especialista. |
| `reservas` | Consultar, reservar e cancelar reservas, ver agenda e taxas. | `sub_agents` com `mode="single_turn"`: a raiz o chama como uma ferramenta. | Reservar salão/churrasqueira precisa de **confirmação**, e a pausa só funciona na raiz ou em `chat`/`single_turn` sob `sub_agents`. |
| `visitantes` | Listar e autorizar visitantes. | Idem. | Liberar acesso também precisa de confirmação. |
| `regulamento` | Responder dúvidas lendo **um capítulo por vez** (`ler_capitulo`). | `AgentTool` na raiz. | Não precisa de confirmação, e a **sessão isolada** do `AgentTool` mantém o texto lido fora dos eventos da sessão (Garantia 4). |

Decisões que valem registrar:

- **`single_turn` e não `AgentTool` para `reservas` e `visitantes`.** Testado na 2.13.0: com `AgentTool` a pausa de confirmação se perde (o `AgentTool` devolve o erro "cannot resume because its nested session is discarded"); com `sub_agents` + `mode="single_turn"` o pedido de confirmação sobe até a raiz e a execução retoma. Com `chat` o especialista passaria a conversar diretamente com o morador e cada um precisaria repetir as regras de conversa; com `single_turn` só a raiz fala com o morador.
- **Camadas.** `db/` (schema, regras de persistência e acesso a dados, sem nada de ADK), `agents/` (agentes e tools) e `web.py` (API). A regra de negócio mora em `db/repo.py`; a tool só valida a entrada, chama o repo e formata a saída. Nenhuma tool recebe apartamento nem chama outra tool.
- **Quem recebe a resposta de uma confirmação.** O `Runner` entrega o `FunctionResponse` ao agente que emitiu o pedido (`adk_request_confirmation`), decisão calculada dos **eventos gravados** (`google/adk/agents/_agent_router.py`). Como o pedido vem do especialista, a retomada funciona também **depois de reiniciar a API**, com a sessão em SQLite. Não foi preciso `ResumabilityConfig` nem `invocation_id`.
- **Robustez em três camadas.** (1) 429/5xx e rede: `HttpRetryOptions` no cliente do Gemini (`agents/assistente_aurora/modelos.py`). (2) Resposta vazia ou malformada do modelo: `ModelRetryPlugin` (`agents/assistente_aurora/plugins.py`). (3) Exceção dentro de uma tool: `on_tool_error_callback` (`agents/assistente_aurora/callbacks.py`). Se o modelo ainda falhar, a API responde **200** com uma mensagem legível em vez de 500.
- **Modelos.** Os nomes vêm do `.env` (`MODELO_PRINCIPAL`, `MODELO_ESPECIALISTA`), nunca do código. Foi validado com `gemini-3.1-flash-lite` nos dois. Um fluxo completo de avaliação faz cerca de 19 chamadas à API de conversa, em torno de 60 chamadas ao modelo (raiz, especialista, raiz de novo).
- **Sem cache de contexto e sem `LoggingPlugin`.** Os prompts são pequenos e o regulamento já fica fora do contexto por arquitetura; por isso não configuramos `context_cache_config` (o ADK avisa disso ao subir a API, é só informativo). O `LoggingPlugin` imprimiria mensagens e argumentos de tools no console, então a entrega não o inclui; para ver agentes, tools e eventos por dentro use o `adk web` (veja abaixo).

## Garantias

Cada garantia vale no **código**, não no que o modelo escolhe fazer.

### 1. Cobrança ou acesso só com confirmação

- `agents/assistente_aurora/tools/reservas_tools.py`, função `reservar_area`: lê a **taxa no banco** (`repo.obter_area`). Se for maior que 0, chama `tool_context.request_confirmation` com `{"area", "data", "taxa"}` e devolve `aguardando_confirmacao` **sem gravar**. Quadra (taxa 0) grava direto.
- `agents/assistente_aurora/tools/visitantes_tools.py`, função `autorizar_visitante`: **sempre** pede confirmação (`{"nome", "data"}`).
- `web.py`, `_confirmacoes_pendentes`: reconstrói as pendências dos eventos da sessão (cada `adk_request_confirmation` sem resposta com o mesmo id) e `/mensagens` as devolve em `confirmacoes_pendentes`.
- `web.py`, `responder_confirmacao` (`POST /sessoes/{id}/confirmacoes`): só aceita um id que esteja pendente **naquela sessão**; qualquer outro (inexistente, já respondido, de outra sessão) → **409** e nada executa. A tool só roda de novo com `tool_confirmation` preenchido, uma vez por aprovação.
- **Por que não depende do modelo:** o modelo só decide *chamar* a tool; a pausa é feita pela própria tool, a taxa vem do banco e a única origem do `FunctionResponse` é a rota. "Já estou confirmando aqui" na conversa não gera nenhuma resposta de confirmação.

### 2. Cada sessão pertence a um apartamento

- `web.py`, `criar_sessao` (`POST /sessoes`): grava `state={"apartamento": ...}` e liga o `session_id` ao apartamento (`repo.registrar_sessao`, tabela `sessoes_apartamento`). É definido **uma única vez**, na criação.
- As tools que tratam dados do morador (`minhas_reservas`, `reservar_area`, `cancelar_reserva`, `meus_visitantes` e `autorizar_visitante`) leem `tool_context.state["apartamento"]`. As demais (`listar_areas`, `verificar_disponibilidade` e `ler_capitulo`) não precisam de apartamento. **Nenhuma tem parâmetro de apartamento**: o schema que o modelo vê não tem esse campo.
- `db/repo.py`, `cancelar_reserva`: o `UPDATE` sempre filtra por `apartamento` e devolve `None` se nada casar. A tool `cancelar_reserva` (`agents/assistente_aurora/tools/reservas_tools.py`) responde então "Não encontrei essa reserva entre as suas", igual para "não existe" e "é de outro apartamento".
- `db/repo.py`, `data_disponivel`: devolve só `True`/`False`, nunca o dono nem o código.
- **Por que não depende do modelo:** mesmo que um prompt convença o modelo a "obedecer", a tool só enxerga o apartamento da sessão e nunca devolve dados de outro.

### 3. Nada se perde no reinício

- `web.py`: `SqliteSessionService` em `.adk/sessoes.db` guarda sessões e eventos; `db/engine.py` guarda os dados do condomínio em `.dados/condominio.db`. A API só cria o schema ao subir (`criar_schema`) e **nunca restaura dados**: isso é o `db/reset.py`.
- As pendências de confirmação saem dos eventos persistidos, então um pedido feito antes do reinício ainda pode ser aprovado depois.
- **Por que não depende do modelo:** tudo está em disco, e o estado que decide algo (sessão, apartamento, pendências) é reconstruído dele.

### 4. O regulamento é consultado, não carregado

- `agents/assistente_aurora/tools/regulamento_tools.py`: `ler_capitulo(numero)` devolve **só aquele capítulo** de `dados/regulamento.md`; `indice_capitulos()` devolve só os títulos.
- `agents/assistente_aurora/subagents/regulamento/agent.py`: a instrução do agente tem **só o índice** dos capítulos.
- `agents/assistente_aurora/agent.py`: a raiz o aciona como `AgentTool`, e a **raiz não recebe o regulamento nas instruções**.
- **Por que não depende do modelo:** o `AgentTool` roda numa sessão aninhada descartada, e só o resumo final volta como resultado da tool. O capítulo lido nunca entra nos eventos da sessão do morador.

### 5. Dois moradores, uma reserva

- `db/engine.py`: `CREATE UNIQUE INDEX ux_reserva_ativa ON reservas(area, data) WHERE status = 'ativa'`. Índice **parcial**: só reservas ativas disputam a data; uma cancelada libera a data e o código dela continua existindo (soft delete), por isso códigos nunca se repetem.
- `db/repo.py`, `criar_reserva`: faz o `INSERT` e trata o `IntegrityError` do índice como `{"status": "ocupada"}`, que vira resposta normal (200, sem erro de servidor). `_inserir_reserva` repete o `INSERT` se o banco estiver bloqueado (`database is locked`), com `busy_timeout` e WAL.
- **Por que não depende do modelo:** a conferência prévia (`data_disponivel`) só deixa a resposta rápida. A exclusividade é decidida pelo banco **no instante da gravação**. Em teste, com duas threads que conferem "livre" antes de gravar, o índice evitou a duplicata nas 20 disputas, e sem o índice as 20 terminaram com duas reservas.

## Como rodar

**Pré-requisitos:** Python 3.12+, [uv](https://docs.astral.sh/uv/) e uma chave do [Google AI Studio](https://aistudio.google.com/apikey).

```bash
git clone <url-do-fork> && cd <pasta-do-fork>
cp .env.example .env          # preencha as variáveis abaixo
uv sync                       # instala o ADK 2.13.0 (versão exata) e as dependências
uv run python -m db.reset     # restaura reservas e visitantes para o estado de dados/*.json
uv run uvicorn web:app --port 8000
```

**Variáveis do `.env`** (o arquivo não é versionado; o `.env.example` só lista os nomes):

| Variável | Para quê |
|---|---|
| `GOOGLE_API_KEY` | Chave do Google AI Studio. |
| `GOOGLE_GENAI_USE_VERTEXAI` | Deixe `FALSE`. |
| `MODELO_PRINCIPAL` | Modelo do agente raiz (validado com `gemini-3.1-flash-lite`). |
| `MODELO_ESPECIALISTA` | Modelo dos especialistas (validado com `gemini-3.1-flash-lite`). |

- A API responde em `http://localhost:8000`. **Restaurar dados** é `uv run python -m db.reset`; reiniciar a API **não** apaga conversas nem dados.
- Rotas: `POST /sessoes` (`{"apartamento": "101"}` → 201 `{"session_id"}`), `POST /sessoes/{id}/mensagens` (`{"texto"}`), `POST /sessoes/{id}/confirmacoes` (`{"id", "confirmado"}`), `GET /sessoes/{id}/eventos`, `GET /apartamentos/{n}/reservas` e `GET /apartamentos/{n}/visitantes`. O arquivo `api.http` traz um roteiro de chamadas (extensão REST Client do VS Code), e `http://localhost:8000/docs` abre a documentação interativa.
- **Ver o assistente por dentro** (agentes, tools, eventos, confirmações, State): `uv run adk web --log_level debug agents`, escolhendo `assistente_aurora`. Ele usa a mesma porta 8000: pare um antes de subir o outro. Em `adk web`, o apartamento vem de `agents/assistente_aurora/initial_state.json`.
- Lint: `uvx ruff check . && uvx ruff format .`.
