from langchain_chroma import Chroma
from .config import CHROMA_PERSIST_DIR, COLLECTION_NAME
from .embeddings import embeddings


def get_vectorstore():
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )


def index_documents(chunks, batch_size=50):
    vectorstore = get_vectorstore()
    total = len(chunks)
    for start in range(0, total, batch_size):
        batch = chunks[start:start + batch_size]
        end = min(start + batch_size, total)
        print(f"Indexing chunks {start + 1}-{end} of {total}...")
        vectorstore.add_documents(batch)
    print(f"Successfully indexed {total} chunks")
    return vectorstore
