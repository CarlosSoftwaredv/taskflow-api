# TaskFlow

O TaskFlow ajuda você a organizar tarefas por status. Ele combina uma interface web simples com uma API REST em FastAPI e autenticação por conta. A interface e a API são servidas pela mesma aplicação.

## Comece pelo Docker

Com o Docker Desktop aberto, no diretório do projeto, execute:

```bash
docker compose up --build -d
```

Abra **http://localhost:8000** no navegador e crie uma conta. A API fica disponível em **http://localhost:8000/docs** e o estado dos serviços em **http://localhost:8000/health**. O MySQL roda em outro container e os dados são guardados no volume `mysql_data`.

Para acompanhar a inicialização:

```bash
docker compose logs -f api db
```

Para parar os containers sem apagar os dados:

```bash
docker compose down
```

## Usar sem Docker

O modo local usa SQLite por padrão:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Em seguida, abra **http://localhost:8000**. O arquivo `taskflow.db` é criado no diretório do projeto.

## O que você pode fazer

- Criar uma conta e entrar com e-mail e senha
- Criar tarefas com título, descrição e status
- Editar e excluir tarefas
- Filtrar tarefas pendentes, em andamento ou concluídas
- Acompanhar o total de tarefas, as que estão em andamento e o progresso concluído
- Usar a API autenticada diretamente pela documentação interativa em `/docs`

## Publicar no Render

O serviço existente pode continuar usando o mesmo repositório conectado e o `Dockerfile` deste projeto. A interface abre na raiz `/`; a documentação continua em `/docs` e a verificação de disponibilidade em `/health`.

No painel do serviço, configure as variáveis de ambiente:

| Variável | Valor |
| --- | --- |
| `APP_ENV` | `production` |
| `SECRET_KEY` | Uma chave aleatória longa e privada |
| `DATABASE_URL` | URL do banco de dados persistente do serviço |

Não reutilize a senha local do Compose como chave de produção. O Render precisa de um banco acessível pelo serviço; o MySQL declarado no `docker-compose.yml` existe apenas no ambiente Docker local.

Depois de enviar as alterações ao repositório ligado ao Render, faça o deploy e verifique `/health`. O Render já publicado em **https://taskflow-api-51ia.onrender.com/docs** é independente do Docker no seu Mac.

## Configuração local

Os valores padrão do Compose são destinados somente ao computador local. Para personalizá-los, copie `.env.example` para `.env` e edite as variáveis. O arquivo `.env` é ignorado pelo Git. Se a porta `3306` ou `8000` já estiver ocupada, altere `MYSQL_PORT` ou `API_PORT`.

## Estrutura

```text
app/
├── routers/       # Rotas de autenticação e tarefas
├── static/        # Interface web do TaskFlow
├── auth.py        # Senhas e tokens JWT
├── crud.py        # Acesso e operações no banco
├── database.py    # Conexão e sessões SQLAlchemy
├── models.py      # Usuários e tarefas
├── schemas.py     # Validação e respostas da API
└── main.py        # Aplicação FastAPI e páginas de estado
```

## API

| Método | Rota | Uso |
| --- | --- | --- |
| `POST` | `/auth/register` | Criar conta |
| `POST` | `/auth/login` | Entrar e receber token |
| `GET` | `/tasks/` | Listar tarefas do usuário |
| `POST` | `/tasks/` | Criar tarefa |
| `GET` | `/tasks/{task_id}` | Consultar tarefa |
| `PUT` | `/tasks/{task_id}` | Atualizar tarefa |
| `DELETE` | `/tasks/{task_id}` | Excluir tarefa |
| `GET` | `/health` | Verificar aplicação e conexão com banco |

As rotas de tarefa exigem um token Bearer. Consulte `/docs` para os formatos de cada requisição.

## Sobre o projeto

Projeto de estudo de desenvolvimento back-end, construído com Python, FastAPI, SQLAlchemy, MySQL/SQLite e Docker.

**Autor:** Carlos Vitor de Moura Borges — estudante de Engenharia de Software e profissional de suporte de TI.
