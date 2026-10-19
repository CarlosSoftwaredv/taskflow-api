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

- Criar uma conta com e-mail único e confirmar o endereço por link
- Recuperar a senha por e-mail com link temporário de uso único
- Entrar com senha e um segundo fator TOTP (Google/Microsoft Authenticator ou 1Password)
- Usar códigos de recuperação de uso único se perder o autenticador
- Consultar usuários e tarefas em uma tela administrativa somente de leitura
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
| `MFA_ENCRYPTION_KEY` | Chave Fernet privada, exclusiva deste ambiente, para criptografar chaves do autenticador |
| `PUBLIC_BASE_URL` | `https://task-k4tz.onrender.com` (sem `/` no fim) |
| `SMTP_HOST` | Host SMTP de um provedor de e-mail transacional |
| `SMTP_PORT` | `587` (STARTTLS) |
| `SMTP_USER` | Usuário SMTP do provedor |
| `SMTP_PASSWORD` | Senha/chave SMTP do provedor |
| `SMTP_FROM` | Remetente verificado no provedor, por exemplo `TaskFlow <nao-responda@seudominio.com>` |
| `DATABASE_VIEWER_KEY` | Chave administrativa aleatória com ao menos 32 caracteres para abrir `/database` |

Não reutilize a senha local do Compose como chave de produção. O Render precisa de um banco acessível pelo serviço; o MySQL declarado no `docker-compose.yml` existe apenas no ambiente Docker local.

Depois de enviar as alterações ao repositório ligado ao Render, faça o deploy e verifique `/health`. A versão publicada está em [https://task-k4tz.onrender.com](https://task-k4tz.onrender.com), com a documentação da API em [https://task-k4tz.onrender.com/docs](https://task-k4tz.onrender.com/docs). Ela é independente do Docker no seu Mac.

Antes de liberar cadastro, redefinição de senha e login no Render, configure as variáveis SMTP, `MFA_ENCRYPTION_KEY` e `DATABASE_VIEWER_KEY` na área **Environment** do serviço. Gere a chave Fernet uma vez com `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`; guarde-a como segredo e não a troque depois que usuários ativarem o autenticador, pois ela protege as chaves MFA armazenadas no banco. Gere a chave do visualizador com `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`. Configure SMTP com um remetente verificado pelo seu provedor. Sem SMTP, a recuperação de senha e a confirmação de e-mail não funcionam. Não coloque esses segredos no GitHub nem no `.env.example`.

Com `DATABASE_VIEWER_KEY` configurada, abra `/database` e informe a chave administrativa. A tela mostra contagens e páginas de usuários e tarefas. É somente leitura e nunca exibe senhas, tokens de redefinição, chaves TOTP ou códigos de recuperação. Mantenha a chave privada; sem ela, a rota de dados fica indisponível.

Senhas novas exigem 12 caracteres, letras e números; ficam protegidas com Argon2. Senhas existentes em bcrypt são atualizadas para Argon2 no próximo login. A sessão expira em 15 minutos. O segundo fator é obrigatório após confirmar o e-mail; códigos de recuperação aparecem apenas uma vez. O banco atual ganha novas tabelas de autenticação automaticamente, sem remover as tabelas existentes de contas e tarefas. Em produção, use conexão privada/TLS com banco persistente, usuário de banco com privilégios mínimos, backups protegidos e segredos exclusivos por ambiente.

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
| `POST` | `/auth/email/resend` | Solicitar reenvio do link de confirmação |
| `POST` | `/auth/email/verify` | Confirmar e-mail usando o token do link |
| `POST` | `/auth/password/forgot` | Solicitar um link de redefinição de senha |
| `POST` | `/auth/password/reset` | Definir nova senha usando o token do link |
| `POST` | `/auth/mfa/setup` | Iniciar configuração do autenticador |
| `POST` | `/auth/mfa/enable` | Ativar o segundo fator e gerar códigos de recuperação |
| `POST` | `/auth/mfa/verify` | Concluir o segundo fator no login |
| `GET` | `/tasks/` | Listar tarefas do usuário |
| `POST` | `/tasks/` | Criar tarefa |
| `GET` | `/tasks/{task_id}` | Consultar tarefa |
| `PUT` | `/tasks/{task_id}` | Atualizar tarefa |
| `DELETE` | `/tasks/{task_id}` | Excluir tarefa |
| `GET` | `/health` | Verificar aplicação e conexão com banco |
| `GET` | `/database` | Abrir a tela protegida de consulta do banco |
| `GET` | `/admin/database/summary` | Ver contagens de dados (requer `X-Database-Viewer-Key`) |
| `GET` | `/admin/database/users` | Consultar usuários (requer chave administrativa) |
| `GET` | `/admin/database/tasks` | Consultar tarefas (requer chave administrativa) |

As rotas de tarefa exigem um token Bearer. Consulte `/docs` para os formatos de cada requisição.

## Sobre o projeto

Projeto de estudo de desenvolvimento back-end, construído com Python, FastAPI, SQLAlchemy, MySQL/SQLite e Docker.

**Autor:** Carlos Vitor de Moura Borges — estudante de Engenharia de Software e profissional de suporte de TI.
