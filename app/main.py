import os
import json
import asyncio
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import redis.asyncio as aioredis

"""
Aplicação TODO (FastAPI)
-----------------------
"""

# -------- Configurações --------
ARQUIVO_DADOS = Path(os.getenv("DATA_FILE", "./data/tasks.json"))
ARQUIVO_DADOS.parent.mkdir(parents=True, exist_ok=True)

URL_REDIS = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TTL_CACHE_SEGUNDOS = int(os.getenv("CACHE_TTL_SECONDS", "60"))



# -------- Modelos de Dados --------
class TarefaBase(BaseModel):
    """Estrutura básica de uma tarefa."""

    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: Optional[str] = Field(default=None, max_length=2000)
    concluida: bool = False


class TarefaCriar(TarefaBase):
    """Payload para criar tarefa."""
    pass


class TarefaAtualizar(BaseModel):
    """Campos opcionais para editar tarefad"""

    titulo: Optional[str] = Field(default=None, min_length=1, max_length=200)
    descricao: Optional[str] = Field(default=None, max_length=2000)
    concluida: Optional[bool] = None


class Tarefa(TarefaBase):
    """Representação completa de uma tarefa, com ID."""

    id: int


# -------- Persistência em arquivo JSON (com trava simples) --------
_trava_arquivo = asyncio.Lock()


async def _ler_todas_as_tarefas() -> List[Tarefa]:
    """Lê todas as tarefas do arquivo JSON"""
    async with _trava_arquivo:
        if not ARQUIVO_DADOS.exists():
            return []
        # Ler o arquivo em thread separada para não travar o loop
        conteudo = await asyncio.to_thread(ARQUIVO_DADOS.read_text)
        if not conteudo.strip():
            return []
        bruto = json.loads(conteudo)
        return [Tarefa(**t) for t in bruto]


async def _gravar_todas_as_tarefas(tarefas: List[Tarefa]) -> None:
    """Grava a lista de tarefas no arquivo JSON"""
    async with _trava_arquivo:
        texto = await asyncio.to_thread(
            json.dumps, [t.model_dump() for t in tarefas], indent=2, ensure_ascii=False
        )
        await asyncio.to_thread(ARQUIVO_DADOS.write_text, texto)


async def _proximo_id(tarefas: List[Tarefa]) -> int:
    """Calcula o próximo ID disponível (sequencial simples)."""
    return max((t.id for t in tarefas), default=0) + 1




# -------- Cache (Redis) --------
cliente_redis: Optional[aioredis.Redis] = None


async def obter_redis() -> Optional[aioredis.Redis]:
    """Obtém um cliente Redis pronto para uso, se possível.
    """

    global cliente_redis
    if cliente_redis is None:
        try:
            cliente_redis = aioredis.from_url(URL_REDIS, decode_responses=True)
            # Ping rápido para validar conectividade
            await cliente_redis.ping()
        except Exception:
            cliente_redis = None
    return cliente_redis


CHAVE_CACHE_TAREFAS = "tasks:all"


async def invalidar_cache_tarefas():
    """Remove o cache da lista de tarefas"""
    r = await obter_redis()
    if r:
        try:
            await r.delete(CHAVE_CACHE_TAREFAS)
        except Exception:
            pass


# -------- Aplicação FastAPI --------
app = FastAPI(title="API de Tarefas (TODO)", version="1.0.0")


@app.on_event("startup")
async def ao_iniciar():
    """Tarefas de inicialização."""
    if not ARQUIVO_DADOS.exists():
        await asyncio.to_thread(ARQUIVO_DADOS.write_text, "[]")
    await obter_redis()  # opcional


@app.get("/health")
async def saude():
    r = await obter_redis()
    return {"status": "ok", "redis": bool(r)}


@app.get("/tasks", response_model=List[Tarefa])
async def listar_tarefas():
    """Lista todas as tarefas. Usa cache se disponível."""
    r = await obter_redis()
    if r:
        try:
            em_cache = await r.get(CHAVE_CACHE_TAREFAS)
            if em_cache:
                bruto = json.loads(em_cache)
                return [Tarefa(**t) for t in bruto]
        except Exception:
            pass

    tarefas = await _ler_todas_as_tarefas()

    if r:
        try:
            await r.set(
                CHAVE_CACHE_TAREFAS,
                json.dumps([t.model_dump() for t in tarefas]),
                ex=TTL_CACHE_SEGUNDOS,
            )
        except Exception:
            pass

    return tarefas


@app.post("/tasks", response_model=Tarefa, status_code=201)
async def adicionar_tarefa(payload: TarefaCriar):
    """Cria uma nova tarefa."""
    tarefas = await _ler_todas_as_tarefas()
    novo_id = await _proximo_id(tarefas)

    tarefa = Tarefa(
        id=novo_id,
        titulo=payload.titulo,
        descricao=payload.descricao,
        concluida=payload.concluida,
    )
    tarefas.append(tarefa)
    await _gravar_todas_as_tarefas(tarefas)
    await invalidar_cache_tarefas()
    return tarefa


@app.put("/tasks/{task_id}", response_model=Tarefa)
async def editar_tarefa(task_id: int, payload: TarefaAtualizar):
    """Edita uma tarefa existente pelo seu ID."""
    tarefas = await _ler_todas_as_tarefas()
    for idx, t in enumerate(tarefas):
        if t.id == task_id:
            atualizado = t.model_copy(
                update={k: v for k, v in payload.model_dump(exclude_unset=True).items()}
            )
            tarefas[idx] = Tarefa(**atualizado.model_dump())
            await _gravar_todas_as_tarefas(tarefas)
            await invalidar_cache_tarefas()
            return tarefas[idx]
    raise HTTPException(status_code=404, detail="Tarefa não encontrada")


# Rota raiz de cortesia
@app.get("/")
async def raiz():
    """Ajuda rápida para começar a usar a API."""
    return {"mensagem": "Bem-vindo à API de Tarefas", "endpoints": ["/health", "/tasks"]}
