import hmac
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

router = APIRouter(prefix="/admin/database", tags=["Administração do banco"])


def require_viewer_key(provided: str | None = Header(default=None, alias="X-Database-Viewer-Key")) -> None:
    expected = os.getenv("DATABASE_VIEWER_KEY", "")
    if len(expected) < 32:
        raise HTTPException(status_code=404, detail="Página indisponível")
    if not provided or not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Chave administrativa inválida")


@router.get("/summary", dependencies=[Depends(require_viewer_key)])
def database_summary(db: Session = Depends(get_db)):
    return {
        "users": db.query(models.User).count(),
        "tasks": db.query(models.Task).count(),
        "pending_email_verifications": (
            db.query(models.User)
            .outerjoin(models.VerifiedEmail, models.VerifiedEmail.user_id == models.User.id)
            .filter(models.VerifiedEmail.user_id.is_(None))
            .count()
        ),
        "enabled_authenticators": db.query(models.Authenticator).filter_by(enabled=True).count(),
    }


@router.get("/users", dependencies=[Depends(require_viewer_key)])
def database_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rows = db.query(models.User).order_by(models.User.id.desc()).offset(offset).limit(limit).all()
    return [{"id": row.id, "name": row.name, "email": row.email, "created_at": _iso(row.created_at)} for row in rows]


@router.get("/tasks", dependencies=[Depends(require_viewer_key)])
def database_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rows = db.query(models.Task).order_by(models.Task.id.desc()).offset(offset).limit(limit).all()
    return [{
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "status": row.status.value,
        "owner_id": row.owner_id,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    } for row in rows]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
