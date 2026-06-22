# app/tools_externas.py
# Ferramenta de integração: consulta um endereço a partir do CEP (API ViaCEP).
# O padrão (schema, timeout, tratamento de erro, validação) serve para
# qualquer API — basta trocar a URL e adicionar autenticação quando preciso.

import httpx
from pydantic import BaseModel, Field
from langchain.tools import tool


# --- Esquema de argumentos: valida a ENTRADA antes de chamar a API ---
class CepArgs(BaseModel):
    cep: str = Field(description="CEP brasileiro de 8 dígitos, somente números")


@tool(args_schema=CepArgs)
def lookup_cep(cep: str) -> str:
    """Consulta o endereço (rua, bairro, cidade, UF) a partir de um CEP
    brasileiro. Use quando o usuário fornecer um CEP e quiser o endereço."""
    # Validação de entrada: normaliza e rejeita cedo o que é inválido.
    cep_clean = "".join(c for c in cep if c.isdigit())
    if len(cep_clean) != 8:
        return "Erro: o CEP deve ter 8 dígitos numéricos."

    try:
        # timeout EXPLÍCITO: nunca deixe uma chamada externa pendurar o agente.
        resp = httpx.get(
            f"https://viacep.com.br/ws/{cep_clean}/json/",
            timeout=5.0,
        )
        # Levanta exceção para status 4xx/5xx (tratada abaixo).
        resp.raise_for_status()
        data = resp.json()

        # Validação de SAÍDA: a API responde 200 mesmo para CEP inexistente,
        # sinalizando com {"erro": true}. Não confie cegamente no 200.
        if data.get("erro"):
            return f"CEP {cep_clean} não encontrado."

        # Transforma o JSON em um texto conciso e legível para o modelo.
        return (
            f"{data.get('logradouro', '')}, {data.get('bairro', '')}, "
            f"{data.get('localidade', '')}-{data.get('uf', '')}"
        )

    # --- Tratamento de erros: cada falha vira uma mensagem clara ---
    except httpx.TimeoutException:
        return "Erro: o serviço de CEP demorou demais para responder. Tente novamente."
    except httpx.HTTPStatusError as exc:
        return f"Erro: o serviço retornou status {exc.response.status_code}."
    except httpx.RequestError:
        return "Erro de rede ao consultar o serviço de CEP. Tente novamente."
    except Exception as exc:
        return f"Erro inesperado ao consultar o CEP: {exc}"
