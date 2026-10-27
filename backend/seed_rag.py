"""
backend/seed_rag.py — Idempotent seeder for isolated demo document RAG.

Indexes strictly approved synthetic CRM and business documents into:
1. SQLite: company_documents & document_chunks tables
2. Chroma: demo_chroma_db/ vector directory

Never ingests personal, academic, or unapproved documents.
"""
import os
import sys
import uuid
import hashlib
import sqlite3
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))

import PyPDF2
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_chroma import Chroma

from backend.rag import get_embeddings, extract_hierarchy, contextualize_chunk
from backend.database import SessionLocal
from backend import models

DEMO_DOCS_DIR = os.path.join(BASE_DIR, "data", "demo_docs")
DEMO_CHROMA_DIR = os.path.join(BASE_DIR, "demo_chroma_db")

# Approved 22 synthetic documents list
APPROVED_ALLOWLIST = [
    "01_B2B_CRM_Intelligence_Landscape.pdf",
    "02_Account_and_Firmographic_Directory.docx",
    "03_Lead_Qualification_and_Pipeline.pdf",
    "04_Contact_and_Stakeholder_Intelligence.txt",
    "05_Customer_Support_and_Service_Cases.pdf",
    "06_Customer_Success_and_Churn_Signals.docx",
    "07_Contract_and_Renewal_Intelligence.pdf",
    "08_Product_and_Commercial_Catalog.txt",
    "09_Marketing_Campaign_Performance.pdf",
    "10_Enterprise_Sales_Forecast.docx",
    "11_External_Business_Intelligence_Brief.pdf",
    "12_Competitive_Intelligence_Notes.txt",
    "13_B2B_Web_and_News_Intelligence.pdf",
    "14_AI_RAG_and_CRM_Governance.docx",
    "15_CRM_Data_Dictionary.txt",
    "16_CRM_Test_Question_Bank.docx",
    "AI_CRM.pdf",
    "Customer_Retention_Policy.pdf",
    "Enterprise_Pricing_Policy.pdf",
    "Product_Catalog.txt",
    "Sales_Discount_Guidelines.docx",
    "Support_SLA_Policy.pdf"
]

def seed_demo_rag(verbose: bool = True) -> Dict[str, Any]:
    embeddings = get_embeddings()
    vectorstore = None
    if not embeddings:
        print("[seed_rag] WARNING: GOOGLE_API_KEY not configured or Embeddings failed. Documents and chunks will be seeded into SQLite, but vector indexing will be skipped.")
    else:
        try:
            os.makedirs(DEMO_CHROMA_DIR, exist_ok=True)
            vectorstore = Chroma(persist_directory=DEMO_CHROMA_DIR, embedding_function=embeddings)
        except Exception as ce:
            print(f"[seed_rag] WARNING: Could not initialize Chroma store: {ce}")
            vectorstore = None

    if not os.path.exists(DEMO_DOCS_DIR):
        print(f"[seed_rag] ERROR: Directory not found: {DEMO_DOCS_DIR}")
        return {"status": "FAILED", "reason": "DEMO_DOCS_DIR missing"}

    db = SessionLocal()


    # Check already indexed documents in Chroma
    existing_sources = set()
    if vectorstore is not None:
        try:
            col = vectorstore._collection
            data = col.get(include=["metadatas"])
            if data and data.get("metadatas"):
                for m in data["metadatas"]:
                    if m and "source" in m:
                        existing_sources.add(m["source"])
        except Exception as e:
            print(f"[seed_rag] Notice: inspecting existing collection: {e}")


    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )

    total_docs = 0
    total_chunks = 0
    skipped_docs = 0

    try:
        for filename in APPROVED_ALLOWLIST:
            file_path = os.path.join(DEMO_DOCS_DIR, filename)
            if not os.path.exists(file_path):
                if verbose:
                    print(f"[seed_rag] Skipping missing allowlist file: {filename}")
                continue

            # Idempotency check: if document already exists in DB and Chroma (or DB already populated when vectorstore unavailable), skip
            existing_doc = db.query(models.CompanyDocument).filter(models.CompanyDocument.filename == filename).first()
            if existing_doc and (
                (filename in existing_sources and existing_doc.index_status == "Indexed")
                or (vectorstore is None and existing_doc.processing_status == "Completed")
            ):
                if verbose:
                    print(f"[seed_rag] Document '{filename}' already processed. Skipping.")
                skipped_docs += 1
                continue


            if verbose:
                print(f"[seed_rag] Processing '{filename}'...")

            ext = os.path.splitext(filename)[1].lower()
            raw_items = []
            if ext == ".pdf":
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for i, page in enumerate(pdf_reader.pages):
                        text = page.extract_text()
                        if text:
                            raw_items.append({"text": text, "page": i + 1})
            elif ext == ".docx":
                doc_file = docx.Document(file_path)
                full_text = "\n".join([p.text for p in doc_file.paragraphs])
                raw_items.append({"text": full_text, "page": None})
            elif ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    full_text = f.read()
                raw_items.append({"text": full_text, "page": None})

            if not raw_items:
                continue

            # Chunking
            final_chunks = []
            for item in raw_items:
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

            if not final_chunks:
                continue

            doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}" if not existing_doc else existing_doc.doc_id
            if not existing_doc:
                company_doc = models.CompanyDocument(
                    doc_id=doc_id,
                    company_id="general",
                    filename=filename,
                    title=os.path.splitext(filename)[0].replace("_", " "),
                    file_type=ext.lstrip("."),
                    file_size=os.path.getsize(file_path),
                    processing_status="Processing",
                    chunk_count=len(final_chunks),
                    index_status="Pending",
                    uploaded_by="USR-SYSTEM"
                )
                db.add(company_doc)
                db.commit()
            else:
                company_doc = existing_doc

            # Prepare chunks
            docs_to_index = []
            for i, chunk_data in enumerate(final_chunks):
                # Deterministic chunk ID
                hash_input = f"{filename}_{i}".encode('utf-8')
                chunk_id = f"CHK-{hashlib.sha256(hash_input).hexdigest()[:8].upper()}"

                contextualized_text = contextualize_chunk(
                    chunk_data["original_text"],
                    company_doc.title or filename,
                    chunk_data["section"],
                    chunk_data["subsection"],
                    chunk_data["page"]
                )

                metadata = {
                    "source": filename,
                    "chunk_sequence": i,
                    "chunk": i,
                    "chunk_id": chunk_id,
                    "parent_doc_id": doc_id,
                    "document_name": company_doc.title or filename,
                    "section": chunk_data["section"] or "",
                    "subsection": chunk_data["subsection"] or "",
                    "page_number": chunk_data["page"] or -1,
                    "source_file_type": ext,
                    "company_id": "general"
                }

                docs_to_index.append(Document(page_content=contextualized_text, metadata=metadata))

                # Insert to SQLite if not present
                existing_chunk = db.query(models.DocumentChunk).filter(models.DocumentChunk.chunk_id == chunk_id).first()
                if not existing_chunk:
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
                        indexing_status="Indexed"
                    )
                    db.add(new_chunk)

            db.commit()

            # Add to Chroma (if vector embedding fails, document and chunk metadata remain in SQLite)
            if vectorstore is not None:
                try:
                    vectorstore.add_documents(docs_to_index)
                    company_doc.index_status = "Indexed"
                except Exception as ve:
                    print(f"[seed_rag] WARNING: Could not index chunks into Chroma for '{filename}': {ve}")
                    company_doc.index_status = "Failed"
            else:
                company_doc.index_status = "Pending"

            company_doc.processing_status = "Completed"
            db.commit()

            total_docs += 1
            total_chunks += len(docs_to_index)

        print(f"[seed_rag] SUCCESS: Processed {total_docs} new documents ({total_chunks} chunks). Skipped {skipped_docs} already indexed.")
        return {
            "status": "OK",
            "indexed_docs": total_docs,
            "indexed_chunks": total_chunks,
            "skipped_docs": skipped_docs
        }
    except Exception as e:
        db.rollback()
        print(f"[seed_rag] Exception during seeding: {e}")
        return {"status": "ERROR", "error": str(e)}
    finally:
        db.close()


def run_seed_rag_safely(verbose: bool = True) -> Dict[str, Any]:
    """Safe wrapper for application startup that never raises an unhandled exception."""
    try:
        return seed_demo_rag(verbose=verbose)
    except Exception as exc:
        print(f"[seed_rag] Non-fatal exception during RAG seeding: {exc}")
        return {"status": "DEGRADED", "error": str(exc)}


if __name__ == "__main__":
    run_seed_rag_safely(verbose=True)

