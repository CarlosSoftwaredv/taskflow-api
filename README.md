# TaskFlow API 📝

API REST para gerenciamento de tarefas (to-do list) com autenticação de usuários via JWT, construída em **Python** com **FastAPI**, **SQLAlchemy** e **MySQL**.

Projeto criado para consolidar conhecimentos práticos de back-end: modelagem de dados, autenticação, versionamento com Git e containerização com Docker.

## ✨ Funcionalidades

- Cadastro e login de usuários com senha criptografada (bcrypt)
- Autenticação via **JWT** (JSON Web Token)
- CRUD completo de tarefas (criar, listar, atualizar, remover)
- Cada usuário só acessa suas próprias tarefas
- Filtro de tarefas por status (`pending`, `in_progress`, `done`)
- Documentação automática interativa (Swagger/OpenAPI)
- Suporte a **MySQL** (produção) e **SQLite** (desenvolvimento local, sem configuração)
- Containerizado com **Docker** e **Docker Compose**
- Testes automatizados com **pytest**

## 🛠️ Tecnologias

| Categoria       | Tecnologia            |
|-----------------|------------------------|
| Linguagem       | Python 3.12            |
| Framework       | FastAPI                |
| ORM             | SQLAlchemy             |
| Banco de dados  | MySQL / SQLite         |
| Autenticação    | JWT (python-jose) + bcrypt |
| Containerização | Docker / Docker Compose|
| Testes          | Pytest                 |

## 📁 Estrutura do projeto

```
taskflow-api/
├── app/
│   ├── routers/
│   │   ├── auth.py       # Endpoints de registro/login
│   │   └── tasks.py      # Endpoints de CRUD de tarefas
│   ├── database.py       # Configuração da conexão com o banco
│   ├── models.py         # Modelos SQLAlchemy (User, Task)
│   ├── schemas.py        # Schemas Pydantic (validação)
│   ├── auth.py           # Hash de senha e geração/validação de JWT
│   ├── crud.py           # Funções de acesso ao banco
│   └── main.py           # Ponto de entrada da aplicação
├── tests/
│   └── test_main.py      # Testes automatizados
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 🚀 Como rodar localmente (sem Docker)

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/taskflow-api.git
cd taskflow-api

# 2. Crie e ative um ambiente virtual
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Rode a aplicação (usa SQLite por padrão, zero configuração)
uvicorn app.main:app --reload
```

Acesse a documentação interativa em: ** https://lnkd.in/dSbjXT36**

## 🐳 Como rodar com Docker (API + MySQL)

```bash
docker-compose up --build
```

A API sobe em `http://localhost:8000` já conectada ao MySQL.

## 🧪 Rodando os testes

```bash
pytest tests/ -v
```

## 📌 Exemplos de uso

**Registrar usuário**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Vitor", "email": "vitor@example.com", "password": "senha123"}'
```

**Login**
```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=vitor@example.com&password=senha123"
```

**Criar tarefa** (use o token retornado no login)
```bash
curl -X POST http://localhost:8000/tasks/ \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Estudar Docker", "status": "pending"}'
```

## 🗺️ Próximos passos (roadmap)

- [ ] Migrations com Alembic
- [ ] Paginação na listagem de tarefas
- [ ] Deploy em nuvem (Render/Railway)
- [ ] Reescrever a versão em Java + Spring Boot para comparar as duas abordagens

## 👤 Autor

**Carlos Vitor de Moura Borges**
Estudante de Engenharia de Software | Suporte de TI na UniEVANGÉLICA

Buscando minha primeira oportunidade como Desenvolvedor de Software.
