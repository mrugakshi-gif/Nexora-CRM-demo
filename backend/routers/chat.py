"""Chat/AI router — preserved logic from main.py."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..ai_agent import process_chat_query, check_llm_health
from ..rag import check_embeddings_health, get_vector_store

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.get("/health")
def chat_health():
    """
    Returns the health/availability status of the AI/RAG system.
    """
    llm_health = check_llm_health()
    emb_health = check_embeddings_health()
    
    chroma_status = "unavailable"
    if emb_health["status"] == "available":
        try:
            vs = get_vector_store()
            if vs:
                chroma_status = "available"
        except Exception:
            chroma_status = "error"
            
    return {
        "llm": llm_health,
        "embeddings": emb_health,
        "vector_store": {
            "configured": emb_health["configured"],
            "status": chroma_status,
            "message": "Chroma available" if chroma_status == "available" else "Chroma initialization failed or embeddings missing"
        }
    }

@router.post("", response_model=schemas.ChatMessageResponse)
def chat_with_agent(
    message: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Submits a user query to the AI Assistant.
    """
    session_id = message.session_id
    
    if session_id:
        chat_session = db.query(models.ChatSession).filter(
            models.ChatSession.session_id == session_id
        ).first()
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if chat_session.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat session")
    else:
        session_id = f"SESS-{uuid.uuid4().hex[:6].upper()}"
        chat_session = models.ChatSession(
            session_id=session_id,
            user_id=current_user.user_id
        )
        db.add(chat_session)
        
    user_msg = models.ChatMessage(
        message_id=f"MSG-{uuid.uuid4().hex[:6].upper()}",
        session_id=session_id,
        role="user",
        content=message.content
    )
    db.add(user_msg)
    db.commit()

    ai_response_text = process_chat_query(
        query=message.content, 
        session=db, 
        user_id=current_user.user_id, 
        role=current_user.role,
        chat_session_id=session_id
    )
    
    new_msg = models.ChatMessage(
        message_id=f"MSG-{uuid.uuid4().hex[:6].upper()}",
        session_id=session_id,
        role="assistant",
        content=ai_response_text
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    
    return new_msg

@router.get("/history", response_model=List[schemas.ChatSessionResponse])
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves chat history for the user.
    """
    sessions = db.query(models.ChatSession).filter(
        models.ChatSession.user_id == current_user.user_id
    ).all()
    return sessions

@router.delete("/{session_id}")
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Deletes a chat session and all its messages.
    """
    chat_session = db.query(models.ChatSession).filter(
        models.ChatSession.session_id == session_id,
        models.ChatSession.user_id == current_user.user_id
    ).first()
    
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id).delete()
    db.delete(chat_session)
    db.commit()
    
    return {"status": "success"}
