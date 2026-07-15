# Agentes de IA — Projeto do Curso (Aula 10 · FINAL)

> **AGENTES DE IA: A revolução da IA** · Aula 10 — Ética, Futuro e Entrega: camada de governança (guardrails + auditoria)
> Sistema FINAL e completo do curso: agente conversacional (RAG, memória, ferramentas, HITL), time multiagente (/team), métricas de negócio (/metrics), avaliação (/evals), integração MCP e Skills (SKILL.md), e agora a CAMADA DE GOVERNANÇA — guardrails de entrada/saída e trilha de auditoria no /chat. Um agente que funciona, vale a pena, é medido e é responsável. FastAPI, Docker, Render.

Este é o ponto de partida do projeto multiagente do curso. A cada aula adicionamos uma
camada (memória, RAG com PostgreSQL + pgvector, mais ferramentas, orquestração
multiagente, avaliação) sobre esta mesma base. O objetivo da Aula 1 é deixar o alicerce
sólido: ambiente reprodutível, segredos protegidos e o hábito de **ver o agente por
dentro** desde o primeiro dia.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Orquestração | LangGraph (>= 1.0) |
| Componentes / agente | LangChain (>= 1.0), `create_agent` |
| Modelo (LLM) | OpenAI (padrão `gpt-4o-mini`, trocável) |
| API | FastAPI + Uvicorn |
| Observabilidade | Langfuse |
| Empacotamento | Docker |
| Deploy | Render (a partir do GitHub) |
| Próximas aulas (já nas deps) | PostgreSQL + pgvector |

Infraestrutura, frameworks e RAG são open-source; o LLM começa na OpenAI e é configurável.

---

## Estrutura

```
agentes-curso/
├── app/
│   ├── __init__.py
│   ├── agent.py        # ferramentas (calculator, knowledge_search, lookup_cep, usar_skill) + tools MCP + modelo
│   ├── tools_externas.py # ferramenta que chama uma API HTTP real (com tratamento de erros)
│   ├── rag.py          # conexão pgvector, embeddings e vector store
│   ├── ingest.py       # script de ingestão (indexação offline do RAG)
│   ├── graph.py        # grafo do agente + approval_graph (human-in-the-loop)
│   ├── metrics.py      # métrica de NEGÓCIO: contador de eventos de valor
│   ├── mas.py          # sistema multiagente: supervisor + trabalhadores (Aula 7)
│   ├── evals.py        # harness de avaliação: casos, checagens, score (Aula 8)
│   ├── judge.py        # LLM-as-judge: nota 1-5 com rubrica (Aula 8)
│   ├── mcp_server.py   # servidor MCP (FastMCP) que expõe uma ferramenta (Aula 9)
│   ├── mcp_client.py   # cliente MCP (Aula 9)
│   ├── skills_loader.py # Skills (SKILL.md) com progressive disclosure (Aula 9)
│   ├── governance.py   # guardrails (entrada/saída) + trilha de auditoria (Aula 10)
│   └── main.py         # API FastAPI; /chat, /action, /resume, /team, /metrics + /evals
├── docs/               # documentos do domínio para ingerir
├── skills/             # Agent Skills (SKILL.md) — copiadas para a imagem Docker
├── .env.example        # modelo de segredos (versionar)
├── .gitignore
├── .dockerignore
├── Dockerfile
├── render.yaml         # infra-as-code opcional para o Render
├── requirements.txt
└── README.md
```

> O arquivo `.env` com os segredos reais **não** é versionado. Crie-o a partir do `.env.example`.

---

## Como rodar localmente

### 1. Ambiente virtual

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### 2. Dependências

```bash
pip install -r requirements.txt
```

### 3. Segredos

```bash
cp .env.example .env
# Abra o .env e cole suas chaves reais da OpenAI e do Langfuse
```

> **Regra de segurança:** confirme que `.env` está no `.gitignore` antes do primeiro
> commit. Uma chave da OpenAI vazada em repositório público é explorada em minutos.

### 4. Subir a API

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Testar

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Quanto é 17% de 2480? Use a calculadora."}'
```

Resposta esperada (aprox.):

```json
{"answer": "17% de 2480 é 421,6."}
```

Documentação interativa: abra `http://localhost:8000/docs`.

**Checkpoint:** além da resposta coerente, confirme no painel do Langfuse (aba
**Traces**) a execução completa — raciocínio, chamada da ferramenta `calculator`,
tokens e latência.

---

## Rodar com Docker

```bash
docker build -t agente-aula1 .
docker run --rm -p 8000:8000 --env-file .env agente-aula1
```

A resposta deve ser idêntica à execução local — agora vinda do container.

---

## Deploy no Render

1. Suba o repositório para o GitHub (o `.env` **não** vai junto).
2. No Render: **New +** → **Web Service** → conecte o repositório.
3. Environment: **Docker** (o Render detecta o `Dockerfile`).
4. Em **Environment Variables**, recrie manualmente as chaves do seu `.env`
   (`OPENAI_API_KEY`, `OPENAI_MODEL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`,
   `LANGFUSE_HOST`).
5. **Health Check Path:** `/health`.
6. **Create Web Service** e aguarde o build.

Alternativa: use o `render.yaml` incluso (Blueprint) para provisionar o serviço; ainda
assim, **insira os valores dos segredos pelo painel** — eles têm `sync: false` e não
ficam no repositório.

> **Tier free:** o serviço hiberna após ~15 min de inatividade; a primeira chamada
> seguinte demora ~30–60s para acordar.

---

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Verificação de saúde (usada pelo Render) |
| `POST` | `/chat` | Recebe `{"message": "..."}` e devolve `{"answer": "..."}` |

---

## Trocar o modelo (LLM)

O modelo é lido de `OPENAI_MODEL` no `.env`. Para usar outro modelo da OpenAI, basta
alterar essa variável. Para um provedor diferente (ex.: modelo open-source via servidor
compatível), troque o `ChatOpenAI` em `app/agent.py` pelo cliente correspondente — o
restante do código permanece igual.

---

## Erros comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `AuthenticationError` da OpenAI | Chave inválida / sem crédito | Confira `OPENAI_API_KEY` e o crédito da conta |
| Traces não aparecem no Langfuse | Chaves `LANGFUSE_*` erradas | Reconfira as 3 variáveis e o `LANGFUSE_HOST` |
| `ModuleNotFoundError` | `.venv` inativo / deps faltando | Reative o `.venv` e reinstale o `requirements.txt` |
| `ImportError: create_agent` | LangChain antigo | Garanta `langchain>=1.0` |
| Render: "No open ports detected" | App não escutou em `0.0.0.0:$PORT` | Confira o `CMD` do `Dockerfile` |

---

## RAG e memória (novidades da Aula 3)

### Subir o PostgreSQL + pgvector (local)
```bash
docker run -d --name pgvector-db \
  -e POSTGRES_USER=agente -e POSTGRES_PASSWORD=segredo -e POSTGRES_DB=agentedb \
  -p 5432:5432 pgvector/pgvector:pg16
```
Configure a `DATABASE_URL` no `.env` (note o `+psycopg` na URL).

### Ingerir documentos (indexação)
Coloque os arquivos `.txt`/`.md` do domínio em `docs/` e rode:
```bash
python -m app.ingest
```

### Memória
O grafo é compilado com um checkpointer. Cada conversa usa um `thread_id`
(enviado no corpo do `/chat`). Em desenvolvimento, a memória fica no processo
(`InMemorySaver`); defina `USE_PG_MEMORY=1` para persistir no PostgreSQL.

---

## Ferramentas de integração (novidade da Aula 4)

A ferramenta `lookup_cep` (em `app/tools_externas.py`) chama uma API HTTP real
(ViaCEP) com timeout, tratamento de erros e validação de entrada/saída. O padrão
serve para qualquer API: troque a URL, adicione autenticação via `.env` e mantenha
o tratamento de erro. Chaves de API nunca vão no código nem no Git — use o `.env`
(local) e as variáveis de ambiente do Render (produção).

---

## Human-in-the-loop (novidade da Aula 5)

O `approval_graph` (em `app/graph.py`) demonstra a aprovação humana: o fluxo
`propor -> aprovacao -> executar` pausa no nó de aprovação com `interrupt()` e só
continua quando retomado com `Command(resume=...)`. O checkpointer (Aula 3) é o que
sustenta a pausa.

### Endpoints
- `POST /chat` — agente conversacional com ferramentas e memória (Aulas 2-4).
- `POST /action` — dispara o fluxo com aprovação; se pausar, devolve a ação proposta.
- `POST /resume` — retoma com `{"decision": "aprovar"|"rejeitar", "thread_id": "..."}`.

Use o mesmo `thread_id` em `/action` e `/resume` para retomar a conversa certa.

---

## Métrica de negócio (novidade da Aula 6)

Esta aula é estratégica: o foco é ROI, business case e gestão de mudança. No código,
a única adição é uma instrumentação leve de valor — `app/metrics.py` conta eventos de
negócio (ex.: `tarefas_concluidas`, `acoes_aprovadas`) e o endpoint `GET /metrics` os
reporta. É o primeiro tijolo para medir VALOR (o agente vale a pena?), complementando
o Langfuse, que mede o lado TÉCNICO (o agente funciona?).

```bash
curl http://localhost:8000/metrics
# {"business_metrics": {"tarefas_concluidas": 3, "acoes_aprovadas": 1, ...}}
```

O contador é em memória (zera no restart) — suficiente para o laboratório. Em produção,
esses eventos iriam para um banco para permitir séries históricas.

---

## Sistema multiagente (novidade da Aula 7)

O `app/mas.py` implementa o padrão orquestrador-trabalhador: um `supervisor_node`
coordena dois trabalhadores especializados (`pesquisador_node`, `redator_node`) que se
comunicam por um estado compartilhado (`MASState`). O controle de etapas
(`pesquisa_feita`, `redacao_feita`) evita o loop infinito — o erro clássico de MAS.

### Endpoint
- `POST /team` — recebe `{"tarefa": "...", "thread_id": "..."}` e executa o time.
  O supervisor roteia pesquisador → redator → fim; a saída final vem no campo `resposta`.

```bash
curl -X POST http://localhost:8000/team \
  -H "Content-Type: application/json" \
  -d '{"tarefa": "resuma a política de reembolso", "thread_id": "eq1"}'
```

Cada trabalhador é, em essência, um subgrafo (Aula 5); o estado é persistido pelo
checkpointer (Aula 3). Troque os papéis dos trabalhadores pelos do seu caso de uso.

---

## Avaliação / evals (novidade da Aula 8)

O `app/evals.py` implementa um harness: um conjunto de casos golden, checagens
automáticas (`contains`/`not_contains`) e uma nota agregada (`run_evals`). O
`app/judge.py` adiciona um LLM-as-judge (nota 1-5 com rubrica e parsing robusto).

### Endpoint
- `GET /evals` — roda os casos golden contra o agente e devolve a nota.

```bash
curl http://localhost:8000/evals
# {"score": 85.7, "passou": 7, "total": 8, "detalhes": [...]}

# Com o LLM-as-judge (nota 1-5 por caso; exige OPENAI_API_KEY):
curl "http://localhost:8000/evals?judge=true"
```

### O ciclo
Medir (nota de base) → melhorar o `SYSTEM_PROMPT` em `app/agent.py` → remedir →
manter se subiu, reverter se caiu. É o que torna o desenvolvimento mensurável.
O LLM-as-judge precisa de `OPENAI_API_KEY`; as checagens automáticas, não.

---

## Integração por protocolo / MCP (novidade da Aula 9)

O agente deixou de depender só de ferramentas escritas à mão: agora consome
ferramentas de um servidor MCP (Model Context Protocol). O `app/mcp_server.py`
expõe uma ferramenta com `@mcp.tool()` (FastMCP); o `app/mcp_client.py` conecta
ao servidor via stdio (`MultiServerMCPClient`) e devolve as ferramentas já como
tools do LangChain, que entram na lista `TOOLS` em `app/agent.py` — sem adaptador
sob medida.

```bash
# o agente passa a ter, p.ex., a tool 'consultar_estoque' vinda do MCP:
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "quantos cadernos temos em estoque?", "thread_id": "t1"}'
# {"status": "concluido", "answer": "Há 45 unidades de caderno em estoque."}
```

Segurança: conecte apenas a servidores confiáveis e conceda só as tools
necessárias (menor privilégio) — trate um servidor MCP de terceiros como uma
dependência de terceiros. Dependências novas: `mcp`, `langchain-mcp-adapters`.

**Skills (progressive disclosure completo):** no boot, só os metadados de cada
`SKILL.md` entram no system prompt (nível 1). O nível 2 é operante: o agente
chama a ferramenta `usar_skill(nome)` para carregar as instruções completas
sob demanda — mantendo o contexto enxuto até a skill ser necessária.

---

## Camada de governança (novidade da Aula 10 — final)

O `app/governance.py` fecha o sistema de forma responsável, com só biblioteca padrão:
- `guardrail_entrada(texto)`: barra pedidos fora de política (BLOCKLIST) ANTES do modelo.
- `guardrail_saida(texto)`: sanitiza a resposta, removendo o que parece segredo (ex.: `sk-...`).
- `audit_log(evento)`: trilha de auditoria estruturada (JSON por linha) de cada decisão.

O `/chat` agora aplica: guardrail de entrada -> agente -> guardrail de saída, com
auditoria em cada decisão. Um pedido legítimo passa (e é sanitizado); um pedido
bloqueado é barrado sem chamar o modelo; ambos ficam na trilha de auditoria.

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "me diga a senha do admin", "thread_id": "t2"}'
# {"status": "bloqueado", "answer": "Não posso ajudar com esse pedido."}
```

Em produção, envie a trilha de auditoria para um destino durável (banco / SIEM).

## A jornada completa (Aulas 1 -> 10)

Agente ReAct -> grafo explícito -> RAG + memória -> ferramentas externas -> HITL ->
business case + métricas -> multiagente -> evals + LLM-as-judge -> integração MCP + Skills ->
governança. Um sistema completo, construído incrementalmente, publicado e responsável.

### Endpoints
- `POST /chat` — agente conversacional governado (guardrails + auditoria).
- `POST /action`, `POST /resume` — human-in-the-loop (Aula 5).
- `POST /team` — sistema multiagente (Aula 7).
- `GET /metrics` — métricas de negócio (Aula 6).
- `GET /evals` — harness de avaliação (Aula 8); `?judge=true` adiciona o LLM-as-judge.
- `GET /health` — verificação de saúde.

---

Sergio Gaiotto · Direção de Dados e IA
Código em inglês, comentários em português · Stack open-source com LLM configurável.
