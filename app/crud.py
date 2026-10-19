from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import hash_password


# ---------- User ----------
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(func.lower(models.User.email) == email.strip().lower()).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ---------- Task ----------
def create_task(db: Session, task: schemas.TaskCreate, owner_id: int) -> models.Task:
    db_task = models.Task(**task.model_dump(), owner_id=owner_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_tasks(db: Session, owner_id: int, status: Optional[models.TaskStatus] = None):
    query = db.query(models.Task).filter(models.Task.owner_id == owner_id)
    if status:
        query = query.filter(models.Task.status == status)
    return query.order_by(models.Task.created_at.desc()).all()


def get_task(db: Session, task_id: int, owner_id: int) -> Optional[models.Task]:
    return (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.owner_id == owner_id)
        .first()
    )


def update_task(db: Session, db_task: models.Task, task_update: schemas.TaskUpdate) -> models.Task:
    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, db_task: models.Task) -> None:
    db.delete(db_task)
    db.commit()
