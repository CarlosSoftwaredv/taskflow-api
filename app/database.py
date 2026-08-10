import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Por padrão usa SQLite local (zero configuração para rodar rápido).
# Em produção/Docker, defina DATABASE_URL apontando para o MySQL, ex:
# mysql+pymysql://user:password@db:3306/taskflow
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./taskflow.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
