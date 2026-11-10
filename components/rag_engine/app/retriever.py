from .vectorstore import get_vectorstore

def retrieve_documents(
    query: str,
    retrieval_k: int = 5,
) -> list:

    vectorstore = get_vectorstore()

    return vectorstore.similarity_search(
        query, 
        k=retrieval_k
    )