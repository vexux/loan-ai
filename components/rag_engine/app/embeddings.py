from langchain_huggingface import HuggingFaceEmbeddings
from .config import LOCAL_EMBEDDING_MODEL

embeddings = HuggingFaceEmbeddings(
    model_name=LOCAL_EMBEDDING_MODEL,
    model_kwargs={"device": "cpu", "local_files_only": True},
    encode_kwargs={"normalize_embeddings": True},
)
