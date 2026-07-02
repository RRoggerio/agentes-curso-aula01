# app/rag.py
# Conexão com o pgvector, modelo de embeddings e fábrica do vector store.

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

load_dotenv()

# Nome da coleção (tabela lógica) onde os vetores ficam guardados.
COLLECTION_NAME = "dominio_conhecimento"


def get_connection_string() -> str:
    """Lê a DATABASE_URL e ajusta o esquema para o driver psycopg3.

    O Render fornece URLs no formato 'postgres://...' (ou 'postgresql://...'),
    mas o SQLAlchemy/langchain-postgres precisa de 'postgresql+psycopg://'.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL não definida. Configure-a no painel do Render "
            "(ou no .env local) apontando para um PostgreSQL com pgvector."
        )
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


# Modelo de embeddings da OpenAI. 'small' é eficiente e barato para começar.
def get_embeddings():
    return OpenAIEmbeddings(model="text-embedding-3-small")


def get_vector_store():
    """Cria o vector store ligado ao pgvector usando a DATABASE_URL do .env."""
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=COLLECTION_NAME,
        connection=get_connection_string(),
        use_jsonb=True,
    )
