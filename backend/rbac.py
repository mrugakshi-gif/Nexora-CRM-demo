from sqlalchemy.orm import Session
from . import models

def get_effective_role(user_role: str) -> str:
    """Normalize legacy role strings into one of three effective RBAC roles."""
    raw = (user_role or "").strip().lower()
    
    if raw in ["admin", "system admin"]:
        return "Admin"
    if raw in ["manager", "sales manager", "sales director", "director"]:
        return "Manager"
    
    # Treat everything else as a Sales Rep (Sales, Sales Rep, SDR, AE, CSM, User, etc.)
    return "Sales Rep"

def get_user_effective_role(session: Session, user: models.User) -> str:
    """Extracts and normalizes the user's role, checking SalesRep if needed."""
    effective_user_role = get_effective_role(user.role)
    if effective_user_role in ["Admin", "Manager"]:
        return effective_user_role
        
    # If the user table says Sales Rep (or generic 'User'), check the sales_reps table.
    if user.rep_id:
        rep = session.query(models.SalesRep).filter(models.SalesRep.rep_id == user.rep_id).first()
        if rep and rep.role:
            rep_effective = get_effective_role(rep.role)
            if rep_effective == "Manager":
                return "Manager"
                
    return "Sales Rep"

def apply_rbac_filter(session: Session, query, user: models.User, model, rep_field: str):
    """
    Applies the object-level RBAC filter to an SQLAlchemy query.
    
    - Admin: bypasses ownership filtering completely (returns query unmodified).
    - Manager: can access records assigned to themselves or any rep they manage.
    - Sales Rep: can access ONLY records assigned to their exact rep_id.
    """
    effective_role = get_user_effective_role(session, user)
    
    if effective_role == "Admin":
        return query
        
    rep_id = user.rep_id
    if not rep_id:
        # If not an Admin and has no rep_id, deny all.
        return query.filter(getattr(model, rep_field) == "NO_REP_ID_DUMMY_RBAC")
        
    if effective_role == "Manager":
        # Find all reps managed by this manager.
        managed_reps = session.query(models.SalesRep.rep_id).filter(
            models.SalesRep.manager_rep_id == rep_id
        ).all()
        managed_rep_ids = [r[0] for r in managed_reps]
        managed_rep_ids.append(rep_id) # Include themselves
        
        return query.filter(getattr(model, rep_field).in_(managed_rep_ids))
        
    # Sales Rep (default)
    return query.filter(getattr(model, rep_field) == rep_id)


def verify_assignment(session: Session, user: models.User, assigned_rep_id: str) -> bool:
    """Check if the user is authorized to assign a record to the given assigned_rep_id."""
    if not assigned_rep_id:
        return True # if None, maybe it's unassigned.
        
    effective_role = get_user_effective_role(session, user)
    if effective_role == "Admin":
        return True
        
    if not user.rep_id:
        return False
        
    if effective_role == "Manager":
        if assigned_rep_id == user.rep_id:
            return True
        # Check if the rep is managed by this manager
        rep = session.query(models.SalesRep).filter(
            models.SalesRep.rep_id == assigned_rep_id,
            models.SalesRep.manager_rep_id == user.rep_id
        ).first()
        return rep is not None
        
    # Sales Rep can only assign to themselves
    return assigned_rep_id == user.rep_id
