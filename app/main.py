from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.routers import auth, tasks

# Cria as tabelas no banco (em produção, prefira migrations com Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TaskFlow API",
    description="API REST para gerenciamento de tarefas, com autenticação JWT.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/", tags=["Status"])
def root(request: Request):
    # Keep the JSON health response for API clients while making the browser
    # experience the task dashboard by default.
    if "text/html" in request.headers.get("accept", ""):
        return FileResponse(Path(__file__).parent / "static" / "index.html")
    return {"status": "online", "service": "TaskFlow API"}


@app.get("/health", tags=["Status"])
def health(db: Session = Depends(get_db)):
    """Readiness endpoint used by the container platform."""
    db.execute(text("SELECT 1"))
    return {"status": "healthy", "service": "TaskFlow API"}
