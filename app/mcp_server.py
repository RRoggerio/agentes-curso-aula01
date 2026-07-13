# app/mcp_server.py
# Servidor MCP: expõe ferramentas no padrão, para qualquer agente consumir.
# Troque 'consultar_estoque' pela ferramenta que seu grupo listou na Aula 8.

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ferramentas-empresa")


@mcp.tool()
def consultar_estoque(produto: str) -> str:
    """Consulta a quantidade em estoque de um produto."""
    # Exemplo didático; aqui entraria a chamada real ao sistema da empresa.
    estoque = {"caneta": 120, "caderno": 45, "mochila": 8}
    qtd = estoque.get(produto.lower())
    if qtd is None:
        return f"Produto '{produto}' não encontrado no estoque."
    return f"Há {qtd} unidades de {produto} em estoque."


if __name__ == "__main__":
    # stdio: o cliente lança este arquivo como subprocesso e conversa por ele.
    mcp.run(transport="stdio")
