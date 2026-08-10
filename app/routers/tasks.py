from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tarefas"])


@router.post("/", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_task(db, task, owner_id=current_user.id)


@router.get("/", response_model=List[schemas.TaskOut])
def list_tasks(
    status_filter: Optional[models.TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_tasks(db, owner_id=current_user.id, status=status_filter)


@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_task = crud.get_task(db, task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return db_task


@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_task = crud.get_task(db, task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return crud.update_task(db, db_task, task_update)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_task = crud.get_task(db, task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    crud.delete_task(db, db_task)
