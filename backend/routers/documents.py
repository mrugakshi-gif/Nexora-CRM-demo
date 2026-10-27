"""Documents router — preserved logic from main.py."""
import os
import shutil
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from .. import models, schemas, rag
from ..database import get_db, SessionLocal
from ..deps import get_current_user
from ..ai_agent import get_authorized_company_ids

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def process_document_background(file_path: str, filename: str, doc_id: str, company_id: Optional[str]):
    db = SessionLocal()
    try:
        rag.process_and_store_document(file_path, filename, doc_id, db, company_id)
    finally:
        db.close()

@router.get("", response_model=List[schemas.CompanyDocumentResponse])
def list_documents(
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.CompanyDocument)
    
    if current_user.role not in ["Admin", "System Admin", "Manager", "Sales Manager"]:
        allowed = get_authorized_company_ids(db, current_user.user_id, current_user.role)
        if allowed:
            if company_id and company_id not in allowed:
                return []
            query = query.filter((models.CompanyDocument.company_id.in_(allowed)) | (models.CompanyDocument.company_id == None))
            
    if company_id:
        query = query.filter(models.CompanyDocument.company_id == company_id)
        
    return query.order_by(models.CompanyDocument.created_at.desc()).all()

@router.get("/{doc_id}/chunks", response_model=List[schemas.DocumentChunkResponse])
def get_document_chunks(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    doc = db.query(models.CompanyDocument).filter(models.CompanyDocument.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role not in ["Admin", "System Admin", "Manager", "Sales Manager"]:
        allowed = get_authorized_company_ids(db, current_user.user_id, current_user.role)
        if allowed and doc.company_id and doc.company_id not in allowed:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
            
    chunks = db.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == doc_id
    ).order_by(models.DocumentChunk.chunk_index.asc()).all()
    
    return chunks

@router.post("/upload", response_model=schemas.CompanyDocumentResponse)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    allowed_extensions = (".pdf", ".docx", ".txt")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported.")
        
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc_id = f"DOC-{uuid.uuid4().hex[:6].upper()}"
    new_doc = models.CompanyDocument(
        doc_id=doc_id,
        filename=file.filename,
        title=file.filename,
        file_type=file.filename.split('.')[-1].upper(),
        file_size=os.path.getsize(file_path),
        processing_status="Uploading",
        company_id=company_id,
        uploaded_by=current_user.user_id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    background_tasks.add_task(process_document_background, file_path, file.filename, doc_id, company_id)
    
    return new_doc

@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    doc = db.query(models.CompanyDocument).filter(models.CompanyDocument.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role not in ["Admin", "System Admin", "Manager", "Sales Manager"]:
        allowed = get_authorized_company_ids(db, current_user.user_id, current_user.role)
        if allowed and doc.company_id and doc.company_id not in allowed:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")
            
    rag.delete_document_from_rag(doc.filename, doc_id, db)
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully"}

from fastapi.responses import FileResponse
@router.get("/{doc_id}/view")
def view_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    doc = db.query(models.CompanyDocument).filter(models.CompanyDocument.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role not in ["Admin", "System Admin", "Manager", "Sales Manager"]:
        auth_company_ids = get_authorized_company_ids(db, current_user.user_id, current_user.role)
        if doc.company_id and doc.company_id not in auth_company_ids:
            raise HTTPException(status_code=403, detail="Not authorized to view this document")
        
    file_path = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing from disk")
        
    return FileResponse(file_path, filename=doc.filename)
