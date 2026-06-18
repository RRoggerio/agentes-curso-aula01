# app/ingest.py
# Indexação (fase offline do RAG): lê docs/, faz chunking, gera
# embeddings e grava no pgvector. Rode uma vez (ou quando a base mudar).

import os
import glob
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.rag import get_vector_store


def load_documents(folder: str = "docs") -> list[Document]:
    """Lê todos os .txt e .md da pasta docs/ como documentos."""
    docs = []
    for path in glob.glob(os.path.join(folder, "*.txt")) + glob.glob(os.path.join(folder, "*.md")):
        with open(path, encoding="utf-8") as f:
            docs.append(Document(page_content=f.read(), metadata={"source": path}))
    return docs


def main():
    # 1. Carrega os documentos do domínio.
    docs = load_documents()
    if not docs:
        print("Nenhum documento em docs/. Adicione .txt ou .md e rode de novo.")
        return

    # 2. Divide em chunks. Overlap evita cortar uma ideia ao meio.
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = splitter.split_documents(docs)
    print(f"{len(docs)} documento(s) -> {len(chunks)} chunk(s)")

    # 3. Gera embeddings e grava no pgvector (uma chamada cuida de tudo).
    store = get_vector_store()
    store.add_documents(chunks)
    print("Ingestão concluída. Vetores gravados no pgvector.")


if __name__ == "__main__":
    main()
