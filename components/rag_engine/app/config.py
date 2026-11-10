from pathlib import Path

# Root of the AgentArchitecture project
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Where documents (PDFs) are stored
DOCUMENTS_DIR = str(PROJECT_ROOT / "data")

# Where ChromaDB persists its index
CHROMA_PERSIST_DIR = str(PROJECT_ROOT / "chroma_db")

# Local embedding model (no API key needed)
LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ChromaDB collection name (domain-agnostic)
COLLECTION_NAME = "agent_knowledge_base"
