from fastapi import FastAPI

from app.database import Base, engine
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
def root():
    return {"status": "online", "service": "TaskFlow API"}
