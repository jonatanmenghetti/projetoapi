# TODO API (FastAPI)

Aplicação simples de Tarefas (TODO List) em Python com FastAPI. Foco nas funcionalidades essenciais do TODO, sem simulações de enriquecimento externo.

Funcionalidades principais:
- Adicionar, listar e editar tarefas.
- Armazenamento em arquivo JSON (simulando banco de dados).
- Cache de lista de tarefas usando Redis com invalidação em gravações.
- Containerização com Docker e orquestração com Docker Compose (API + Redis).

## Requisitos
- Docker e Docker Compose

Opcional (para rodar localmente sem Docker):
- Python 3.11+

## Como executar com Docker Compose

1. Build e subir serviços:

   docker compose up --build

2. A API ficará disponível em:

   http://localhost:8000

3. Endpoints úteis:
- GET /health — status simples e conectividade com Redis.
- GET /tasks — lista tarefas (usa cache Redis quando disponível).
- POST /tasks — adiciona tarefa.
- PUT /tasks/{id} — edita tarefa.

Exemplos de uso via curl:
- Criar uma tarefa:

  curl -X POST http://localhost:8000/tasks \
       -H 'Content-Type: application/json' \
       -d '{"titulo": "Estudar Otimização de Sistemas em Nuvem", "descricao": "Ler Conteúdo", "concluida": false}'

- Listar tarefas:

  curl http://localhost:8000/tasks

- Editar tarefa:

  curl -X PUT http://localhost:8000/tasks/1 \
       -H 'Content-Type: application/json' \
       -d '{"concluida": true}'

## Variáveis de Ambiente
- DATA_FILE: caminho do arquivo JSON (default: /data/tasks.json no container; ./data/tasks.json localmente).
- REDIS_URL: URL de conexão Redis (ex: redis://redis:6379/0 no Compose; redis://localhost:6379/0 local).
- CACHE_TTL_SECONDS: TTL do cache da lista (default: 60s).

## Executar localmente sem Docker (opcional)
1. Criar venv e instalar dependências:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Iniciar Redis localmente (se quiser cache):
- Via Docker:

  docker run --name todo-redis -p 6379:6379 -d redis:7-alpine

3. Iniciar API:

   uvicorn app.main:app --host 0.0.0.0 --port 8000

## Notas
- Cache: GET /tasks utiliza Redis; escritas (POST/PUT) invalidam o cache. A API funciona sem Redis (apenas sem cache).

## Deploy em Nuvem (Opcional)
- Você pode usar o Dockerfile para publicar em serviços como Render/Heroku/Railway/Fly.io. Em ambientes sem Redis, a API continua funcional (apenas sem cache), pois a conexão é opcional e tolerante a falhas.


## URL do Serviço
- Local (Docker Compose): http://localhost:8000
- Nuvem (se houver): substitua aqui pelo link do seu deploy, por exemplo: https://seu-servico-na-nuvem.example.com
