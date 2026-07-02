# Agentes de IA — Projeto do Curso (Aula 6)

> **AGENTES DE IA: A revolução da IA** · Aula 6 — IA Agêntica nos Negócios: métrica de negócio instrumentada no agente
> Agente completo (RAG, memória, ferramentas, human-in-the-loop) agora com uma métrica de NEGÓCIO instrumentada: um contador de eventos de valor exposto em /metrics, complementando a observabilidade técnica do Langfuse. Exposto por FastAPI, em Docker e publicado no Render.

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
│   ├── agent.py        # ferramentas (calculator, knowledge_search, lookup_cep) + modelo
│   ├── tools_externas.py # ferramenta que chama uma API HTTP real (com tratamento de erros)
│   ├── rag.py          # conexão pgvector, embeddings e vector store
│   ├── ingest.py       # script de ingestão (indexação offline do RAG)
│   ├── graph.py        # grafo do agente + approval_graph (human-in-the-loop)
│   ├── metrics.py      # métrica de NEGÓCIO: contador de eventos de valor
│   └── main.py         # API FastAPI; /chat, /action, /resume + /metrics (negócio)
├── docs/               # documentos do domínio para ingerir
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

Sergio Gaiotto · Direção de Dados e IA
Código em inglês, comentários em português · Stack open-source com LLM configurável.
