"""
Workspace & member management endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from api.db import (
    get_db, User, Workspace, WorkspaceMember, create_workspace, PLAN_LIMITS,
)
from api.auth import get_current_user

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class InviteMember(BaseModel):
    email: str
    role:  str = Field("viewer", pattern="^(editor|viewer)$")


@router.post("", status_code=201)
def create_ws(body: WorkspaceCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ws = create_workspace(db, body.name, user)
    return _ws_response(ws, db)


@router.get("")
def list_workspaces(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user.id
    ).all()
    result = []
    for m in memberships:
        ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
        if ws:
            r = _ws_response(ws, db)
            r["my_role"] = m.role
            result.append(r)
    return {"workspaces": result, "total": len(result)}


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ws = _get_member_ws(db, workspace_id, user.id)
    return _ws_response(ws, db)


@router.post("/{workspace_id}/members")
def invite_member(
    workspace_id: str, body: InviteMember,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    ws = _get_member_ws(db, workspace_id, user.id, required_role="owner")

    # Check seat limits
    limit = PLAN_LIMITS.get(ws.plan_tier, {}).get("seats")
    if limit is not None:
        current = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id
        ).count()
        if current >= limit:
            raise HTTPException(
                402, f"Seat limit reached ({current}/{limit}). Upgrade your plan."
            )

    invitee = db.query(User).filter(User.email == body.email, User.active == True).first()
    if not invitee:
        raise HTTPException(404, f"No user found with email '{body.email}'.")

    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == invitee.id,
    ).first()
    if existing:
        raise HTTPException(409, "User is already a member.")

    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=invitee.id,
        role=body.role,
    )
    db.add(member)
    db.commit()
    return {"status": "added", "email": body.email, "role": body.role}


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
def remove_member(
    workspace_id: str, user_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _get_member_ws(db, workspace_id, user.id, required_role="owner")
    if user_id == user.id:
        raise HTTPException(400, "Cannot remove yourself from workspace.")
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(404, "Member not found.")
    db.delete(member)
    db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_member_ws(
    db: Session, workspace_id: str, user_id: str, required_role: str = "viewer"
) -> Workspace:
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(404, "Workspace not found or access denied.")
    role_order = {"viewer": 0, "editor": 1, "owner": 2}
    if role_order.get(member.role, 0) < role_order.get(required_role, 0):
        raise HTTPException(403, f"Requires '{required_role}' role.")
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found.")
    return ws


def _ws_response(ws: Workspace, db: Session) -> dict:
    member_count = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws.id
    ).count()
    from api.db import CustomPersona
    persona_count = db.query(CustomPersona).filter(
        CustomPersona.workspace_id == ws.id
    ).count()
    limits = PLAN_LIMITS.get(ws.plan_tier, {})
    return {
        "id":           ws.id,
        "name":         ws.name,
        "plan_tier":    ws.plan_tier,
        "member_count": member_count,
        "persona_count":persona_count,
        "limits":       limits,
        "created_at":   ws.created_at.isoformat() if ws.created_at else None,
    }
