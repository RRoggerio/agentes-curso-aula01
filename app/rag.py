# app/rag.py
# Conexão com o pgvector, modelo de embeddings e fábrica do vector store.

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

load_dotenv()

# Nome da coleção (tabela lógica) onde os vetores ficam guardados.
COLLECTION_NAME = "dominio_conhecimento"


# Modelo de embeddings da OpenAI. 'small' é eficiente e barato para começar.
def get_embeddings():
    return OpenAIEmbeddings(model="text-embedding-3-small")


def get_vector_store():
    """Cria o vector store ligado ao pgvector usando a DATABASE_URL do .env."""
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=COLLECTION_NAME,
        connection=os.getenv("DATABASE_URL"),
        use_jsonb=True,
    )
