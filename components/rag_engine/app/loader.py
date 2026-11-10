from pathlib import Path
import pymupdf
from langchain_core.documents import Document
from .config import DOCUMENTS_DIR


def load_pdf(pdf_path: str) -> list[Document]:
    documents = []
    pdf = pymupdf.open(pdf_path)
    for page_number, page in enumerate(pdf, start=1):
        text = page.get_text("text").strip()
        if not text:
            continue
        documents.append(
            Document(
                page_content=text,
                metadata={"source": Path(pdf_path).name, "page": page_number},
            )
        )
    pdf.close()
    return documents


def load_text_or_md(file_path: str) -> list[Document]:
    path = Path(file_path)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [
        Document(
            page_content=text,
            metadata={"source": path.name, "page": 1},
        )
    ]


def load_all_documents() -> list[Document]:
    documents = []
    documents_dir = Path(DOCUMENTS_DIR)

    # 1. Load PDFs
    for pdf_path in documents_dir.glob("*.pdf"):
        print(f"Loading PDF: {pdf_path.name}")
        documents.extend(load_pdf(str(pdf_path)))

    # 2. Load Markdown & Text files
    for doc_path in list(documents_dir.glob("*.md")) + list(documents_dir.glob("*.txt")):
        print(f"Loading Text/MD: {doc_path.name}")
        documents.extend(load_text_or_md(str(doc_path)))

    print(f"Loaded {len(documents)} document sections")
    return documents

load_all_pdfs = load_all_documents