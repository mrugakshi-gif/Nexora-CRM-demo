import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2
import docx

CHROMA_DIR_NAME = os.environ.get("CHROMA_DB_DIR", "demo_chroma_db")
DB_DIR = os.path.join(BASE_DIR, CHROMA_DIR_NAME)
if not os.path.exists(DB_DIR) and os.path.exists(os.path.join(BASE_DIR, "chroma_db")):
    DB_DIR = os.path.join(BASE_DIR, "chroma_db")

def check_embeddings_health() -> dict:
    """Check health of Google Embeddings."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"configured": False, "status": "unavailable", "message": "GOOGLE_API_KEY missing"}

    try:
        emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
        return {"configured": True, "status": "available", "message": "Embeddings initialized"}
    except Exception as e:
        return {"configured": True, "status": "error", "message": str(e)}

def get_embeddings():
    """Initializes Google Embeddings if API key is present."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Warning: GOOGLE_API_KEY is not set. Google Embeddings will not be available.")
        return None
    try:
        return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    except Exception as e:
        print(f"Warning: Could not initialize Google Embeddings. Error: {e}")
        return None

# Lazy singleton — do NOT call get_embeddings() at module import time.
# The first call to _get_embeddings_cached() initialises the object and
# caches it; every subsequent call returns the cached instance instantly.
_embeddings_cache = None

def _get_embeddings_cached():
    """Returns a cached GoogleGenerativeAIEmbeddings instance (lazy init)."""
    global _embeddings_cache
    if _embeddings_cache is None:
        _embeddings_cache = get_embeddings()
    return _embeddings_cache


_vectorstore_cache = None

def get_vector_store():
    """Returns the ChromaDB vector store instance."""
    global _vectorstore_cache
    if _vectorstore_cache is not None:
        return _vectorstore_cache

    emb = _get_embeddings_cached()
    if not emb:
        return None

    _vectorstore_cache = Chroma(persist_directory=DB_DIR, embedding_function=emb)
    return _vectorstore_cache


def extract_hierarchy(text, ext):
    """Simple heuristic to extract section hierarchy from text."""
    # This is a basic implementation. Real NLP or specialized parsers would be better.
    lines = text.split('\n')
    section = "General"
    subsection = None
    structured_chunks = []

    current_chunk = []

    for line in lines:
        stripped = line.strip()
        # Very basic markdown heading detection
        if stripped.startswith("## "):
            if current_chunk:
                structured_chunks.append({"text": "\n".join(current_chunk), "section": section, "subsection": subsection})
                current_chunk = []
            subsection = stripped[3:].strip()
        elif stripped.startswith("# "):
            if current_chunk:
                structured_chunks.append({"text": "\n".join(current_chunk), "section": section, "subsection": subsection})
                current_chunk = []
            section = stripped[2:].strip()
            subsection = None
        else:
            current_chunk.append(line)

    if current_chunk:
        structured_chunks.append({"text": "\n".join(current_chunk), "section": section, "subsection": subsection})

    return structured_chunks

def contextualize_chunk(original_text, doc_title, section, subsection, page_number):
    """Attempt optional LLM contextualization, fallback to deterministic."""
    # Deterministic fallback
    hierarchy = [doc_title]
    if section and section != "General":
        hierarchy.append(section)
    if subsection:
        hierarchy.append(subsection)
    if page_number is not None:
        hierarchy.append(f"Page {page_number}")

    prefix = f"[{' > '.join(hierarchy)}]: "
    return f"{prefix}\n{original_text.strip()}"

def process_and_store_document(file_path: str, filename: str, doc_id: str, db, company_id: str = None) -> bool:
    """
    Extracts text from a PDF, DOCX, or TXT, chunks it, stores chunks in DB, and indexes in ChromaDB.
    """
    from . import models
    import uuid
    import os
    import PyPDF2
    import docx
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document

    doc = db.query(models.CompanyDocument).filter(models.CompanyDocument.doc_id == doc_id).first()
    if not doc:
        return False

    try:
        if not _get_embeddings_cached():
            raise Exception("Embeddings not configured.")


        # 1. Extracting Text with metadata
        doc.processing_status = "Extracting"
        db.commit()

        ext = os.path.splitext(filename)[1].lower()
        raw_items = [] # list of dicts: text, page

        if ext == ".pdf":
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for i, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        raw_items.append({"text": page_text, "page": i + 1})
        elif ext == ".docx":
            doc_file = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc_file.paragraphs])
            raw_items.append({"text": full_text, "page": None})
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                full_text = f.read()
            raw_items.append({"text": full_text, "page": None})
        else:
            raise Exception(f"Unsupported file format: {ext}")

        if not raw_items:
            raise Exception("No text extracted.")

        # 2. Chunking
        doc.processing_status = "Chunking"
        db.commit()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        final_chunks = []
        for item in raw_items:
            # basic hierarchy extraction
            struct_chunks = extract_hierarchy(item["text"], ext)
            for sc in struct_chunks:
                if not sc["text"].strip():
                    continue
                splits = text_splitter.split_text(sc["text"])
                for s in splits:
                    final_chunks.append({
                        "original_text": s,
                        "section": sc["section"],
                        "subsection": sc["subsection"],
                        "page": item["page"]
                    })

        # 3. Generating Embeddings
        doc.processing_status = "Generating Embeddings"
        doc.chunk_count = len(final_chunks)
        db.commit()

        docs_to_index = []
        for i, chunk_data in enumerate(final_chunks):
            chunk_id = f"CHK-{uuid.uuid4().hex[:8].upper()}"

            # Contextualize
            contextualized_text = contextualize_chunk(
                chunk_data["original_text"],
                doc.title or filename,
                chunk_data["section"],
                chunk_data["subsection"],
                chunk_data["page"]
            )

            metadata = {
                "source": filename,
                "chunk_sequence": i,
                "chunk_id": chunk_id,
                "parent_doc_id": doc_id,
                "document_name": doc.title or filename,
                "section": chunk_data["section"] or "",
                "subsection": chunk_data["subsection"] or "",
                "page_number": chunk_data["page"] or -1,
                "source_file_type": ext,
                "company_id": company_id if company_id else "general"
            }
            docs_to_index.append(Document(page_content=contextualized_text, metadata=metadata))

            # Save chunk to DB
            new_chunk = models.DocumentChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                chunk_index=i,
                original_text=chunk_data["original_text"],
                text=contextualized_text,
                section=chunk_data["section"],
                subsection=chunk_data["subsection"],
                source_file_type=ext,
                page_number=chunk_data["page"],
                character_count=len(chunk_data["original_text"]),
                token_count=None,
                indexing_status="Indexed"
            )
            db.add(new_chunk)

        db.commit()

        # 4. Indexing in Chroma
        vectorstore = get_vector_store()
        vectorstore.add_documents(docs_to_index)

        # 5. Completed
        doc.processing_status = "Completed"
        doc.index_status = "Indexed"
        db.commit()
        return True
    except Exception as e:
        print(f"Error processing document: {e}")
        doc.processing_status = "Failed"
        doc.index_status = str(e)[:255]
        db.commit()
        return False

def delete_document_from_rag(filename: str, doc_id: str, db) -> bool:
    """Deletes all chunks associated with a filename from ChromaDB and DB."""
    try:
        # Delete from DB (cascade might handle it, but being explicit)
        from . import models
        db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc_id).delete()
        db.commit()

        vectorstore = get_vector_store()
        if not vectorstore:
            return False
        # Chroma python client allows deletion by where clause
        collection = vectorstore._collection
        collection.delete(where={"source": filename})
        return True
    except Exception as e:
        print(f"Error deleting document from RAG: {e}")
        return False

def get_rag_retriever(company_ids: list = None):
    """Returns a retriever interface for the vector store with company_id filtering."""
    vectorstore = get_vector_store()
    if not vectorstore:
        return None

    search_kwargs = {"k": 3}
    if company_ids:
        # ChromaDB syntax for 'in' list filter
        search_kwargs["filter"] = {"company_id": {"$in": company_ids}}

    return vectorstore.as_retriever(search_kwargs=search_kwargs)
