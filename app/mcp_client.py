# app/mcp_client.py
# Conecta ao(s) servidor(es) MCP e devolve as ferramentas como tools LangChain.

import asyncio
import concurrent.futures
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient


# Mapa de servidores MCP. Cada um diz como ser lançado.
# Aqui, lançamos nosso próprio servidor via stdio (mesmo Python do projeto).
SERVIDORES = {
    "empresa": {
        "command": sys.executable,          # o python atual
        "args": ["-m", "app.mcp_server"],     # roda app/mcp_server.py
        "transport": "stdio",
    }
}


async def _carregar_tools_async():
    client = MultiServerMCPClient(SERVIDORES)
    # get_tools faz a descoberta: pergunta ao servidor quais ferramentas existem.
    return await client.get_tools()


def _rodar_sincrono(coro_func):
    """Executa uma coroutine de forma síncrona nos dois cenários de boot.

    Rodando como script (ex.: `python -c ...`) não há event loop ativo,
    então asyncio.run() basta. Mas o uvicorn importa o app de DENTRO do
    seu próprio event loop; ali asyncio.run() levanta 'cannot be called
    from a running event loop'. Nesse caso delegamos a uma thread separada,
    que tem seu próprio loop e não conflita com o do servidor.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Nenhum loop rodando nesta thread: caminho direto.
        return asyncio.run(coro_func())
    # Já existe um loop rodando (boot do uvicorn): roda numa thread própria.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro_func())).result()


def carregar_tools_mcp():
    """Carrega as tools MCP de forma síncrona (chamado uma vez, no boot)."""
    try:
        return _rodar_sincrono(_carregar_tools_async)
    except Exception as e:
        # Se o servidor MCP não subir, seguimos sem as tools externas.
        print(f"[MCP] não foi possível carregar tools: {e}")
        return []
