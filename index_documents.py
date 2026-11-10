"""
One-time script to index documents from the data/ folder into ChromaDB.
Run this once before starting the agent whenever you add new documents.

Usage:
    python index_documents.py
"""
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from components.rag_engine.app.loader import load_all_pdfs
from components.rag_engine.app.splitter import split_documents
from components.rag_engine.app.vectorstore import index_documents
from components.rag_engine.app.config import DOCUMENTS_DIR, CHROMA_PERSIST_DIR


def main():
    print(f"📂 Loading documents from: {DOCUMENTS_DIR}")

    documents = load_all_pdfs()

    if not documents:
        print("⚠️  No PDF files found in the data/ folder.")
        print(f"    Place PDF files in: {DOCUMENTS_DIR}")
        return

    print(f"✂️  Splitting {len(documents)} pages into chunks...")
    chunks = split_documents(documents)
    print(f"    Created {len(chunks)} chunks.")

    print("🔢 Embedding and indexing into ChromaDB...")
    index_documents(chunks)

    print(f"\n✅ Done! ChromaDB index saved to: {CHROMA_PERSIST_DIR}")
    print("    You can now run the agent.")


if __name__ == "__main__":
    main()
