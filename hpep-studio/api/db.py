"""
HPEP Studio — Database models.
Workspaces, custom personas, version history, scenarios.
"""

import os
import json
import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey,
    Integer, Float, Text, create_engine, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker, Session

DATABASE_URL = os.getenv("STUDIO_DATABASE_URL", "sqlite:///./hpep_studio.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# ── Models ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "studio_users"

    id         = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    email      = Column(String(254), unique=True, nullable=False, index=True)
    api_key    = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    active     = Column(Boolean, default=True)

    workspaces   = relationship("WorkspaceMember", back_populates="user", lazy="select")
    owned_spaces = relationship("Workspace", back_populates="owner", lazy="select")

    @staticmethod
    def generate_api_key() -> str:
        return "hpep_" + secrets.token_hex(28)


class Workspace(Base):
    __tablename__ = "workspaces"

    id         = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    name       = Column(String(128), nullable=False)
    owner_id   = Column(String(36), ForeignKey("studio_users.id"), nullable=False, index=True)
    plan_tier  = Column(String(16), default="free")  # "free"|"studio"|"team"|"enterprise"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner    = relationship("User", back_populates="owned_spaces")
    members  = relationship("WorkspaceMember", back_populates="workspace", lazy="select")
    personas = relationship("CustomPersona", back_populates="workspace", lazy="select")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)

    id           = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id      = Column(String(36), ForeignKey("studio_users.id"), nullable=False, index=True)
    role         = Column(String(16), default="viewer")  # "owner"|"editor"|"viewer"
    joined_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace", back_populates="members")
    user      = relationship("User", back_populates="workspaces")


class CustomPersona(Base):
    __tablename__ = "custom_personas"

    id               = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    workspace_id     = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    name             = Column(String(128), nullable=False)
    description      = Column(Text, nullable=True)
    blocks_json      = Column(Text, nullable=False)   # {"1": 0.72, "2": 0.85, ...} B1-B10
    k_overrides_json = Column(Text, nullable=True)    # {"0": 0.95, "11": 0.88, ...} K0-K99
    ceid_score       = Column(Float, nullable=True)   # cached at save
    version          = Column(Integer, default=1)
    is_public        = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace", back_populates="personas")
    versions  = relationship("PersonaVersion", back_populates="persona", lazy="select",
                             cascade="all, delete-orphan",
                             order_by="PersonaVersion.version.desc()")

    def get_blocks(self) -> dict:
        return json.loads(self.blocks_json)

    def get_k_overrides(self) -> dict:
        return json.loads(self.k_overrides_json) if self.k_overrides_json else {}


class PersonaVersion(Base):
    __tablename__ = "persona_versions"

    id           = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    persona_id   = Column(String(36), ForeignKey("custom_personas.id"), nullable=False, index=True)
    version      = Column(Integer, nullable=False)
    blocks_json  = Column(Text, nullable=False)
    k_overrides_json = Column(Text, nullable=True)
    ceid_score   = Column(Float, nullable=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    persona = relationship("CustomPersona", back_populates="versions")


class Scenario(Base):
    __tablename__ = "scenarios"

    id               = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    workspace_id     = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    title            = Column(String(256), nullable=False)
    description      = Column(Text, nullable=True)
    persona_ids_json = Column(Text, nullable=False)   # ["persona_id_1", ...]
    task_description = Column(Text, nullable=False)
    context          = Column(Text, nullable=True)
    difficulty       = Column(String(16), default="medium")  # "easy"|"medium"|"hard"
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    runs = relationship("ScenarioRun", back_populates="scenario", lazy="select")


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id                = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    scenario_id       = Column(String(36), ForeignKey("scenarios.id"), nullable=False, index=True)
    user_id           = Column(String(36), ForeignKey("studio_users.id"), nullable=False)
    conversation_json = Column(Text, nullable=True)
    score             = Column(Float, nullable=True)
    completed_at      = Column(DateTime, nullable=True)
    started_at        = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    scenario = relationship("Scenario", back_populates="runs")


# ── Init & helpers ─────────────────────────────────────────────────────────────

def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_by_api_key(db: Session, api_key: str) -> "User | None":
    return db.query(User).filter(User.api_key == api_key, User.active == True).first()


def get_user_by_email(db: Session, email: str) -> "User | None":
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str) -> User:
    user = User(email=email, api_key=User.generate_api_key())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_workspace(db: Session, name: str, owner: User, plan_tier: str = "free") -> Workspace:
    ws = Workspace(name=name, owner_id=owner.id, plan_tier=plan_tier)
    db.add(ws)
    db.flush()
    member = WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner")
    db.add(member)
    db.commit()
    db.refresh(ws)
    return ws


def get_workspace(db: Session, workspace_id: str, user_id: str) -> "Workspace | None":
    """Return workspace only if user is a member."""
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    ).first()
    if not member:
        return None
    return db.query(Workspace).filter(Workspace.id == workspace_id).first()


PLAN_LIMITS = {
    "free":       {"personas": 3,   "calls_per_month": 50,    "seats": 1},
    "studio":     {"personas": 50,  "calls_per_month": 2000,  "seats": 1},
    "team":       {"personas": None,"calls_per_month": 10000, "seats": 5},
    "enterprise": {"personas": None,"calls_per_month": None,  "seats": None},
}
