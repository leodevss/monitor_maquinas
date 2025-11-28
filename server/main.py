# main.py
import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseSettings
import asyncpg

# -------------------------
# Config
# -------------------------
class Settings(BaseSettings):
    DATABASE_URL: Optional[str] = None
    API_KEY: Optional[str] = ""
    APP_TITLE: str = "Monitor de Recursos - Server"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitor-server")

if not settings.DATABASE_URL:
    logger.warning("DATABASE_URL não configurada (env). Endpoints de DB irão falhar.")

# -------------------------
# App & Static files
# -------------------------
app = FastAPI(title=settings.APP_TITLE)

# Mount static directory (mais eficiente que endpoint manual)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.isdir(static_dir):
    os.makedirs(static_dir, exist_ok=True)  # opcional — cria pasta para evitar erros
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# -------------------------
# Pool de conexões (asyncpg)
# -------------------------
db_pool: Optional[asyncpg.pool.Pool] = None

@app.on_event("startup")
async def startup():
    global db_pool
    if settings.DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL, min_size=1, max_size=10)
            logger.info("Pool de DB criado com sucesso.")
        except Exception as e:
            db_pool = None
            logger.error(f"Falha ao criar pool de DB: {e}")
    else:
        logger.warning("DATABASE_URL ausente — pool de DB não criado.")

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Pool de DB fechado.")

# -------------------------
# Helpers
# -------------------------
def require_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Dependência simples para proteger endpoints sensíveis.
    Você pode enviar header: X-API-KEY: <sua chave>
    """
    if not settings.API_KEY:
        # chave não configurada -> não exigir (modo dev)
        return True
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")
    return True

# -------------------------
# Endpoints
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    html = """
    <html><head><meta charset="utf-8"><title>Monitor</title></head>
    <body>
      <h2>Monitor de Recursos - Servidor</h2>
      <p><a href="/static/grafico.html">Abrir gráfico</a></p>
      <p><a href="/health">Health check</a></p>
      <p><a href="/db_test">Testar conexão DB</a> (gera/insere/conta)</p>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}

@app.get("/db_test")
async def db_test(_=Depends(require_api_key)):
    """
    Testa conexão com o banco:
    - cria tabela de teste se não existir
    - insere uma linha com timestamp e cpu%, ram%
    - retorna a contagem de linhas da tabela
    """
    global db_pool
    if not db_pool:
        raise HTTPException(status_code=500, detail="Pool de DB não disponível. Verifique DATABASE_URL e logs.")

    async with db_pool.acquire() as conn:
        # usar transação para segurança
        async with conn.transaction():
            # criar tabela (apenas para teste; use migrations em produção)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS measurements_test (
                    id SERIAL PRIMARY KEY,
                    ts TIMESTAMP NOT NULL,
                    cpu_percent REAL,
                    ram_percent REAL
                );
            """)
            # inserir registro exemplo
            row_id = await conn.fetchval(
                "INSERT INTO measurements_test (ts, cpu_percent, ram_percent) VALUES (NOW(), $1, $2) RETURNING id;",
                12.34, 56.78
            )
            total = await conn.fetchval("SELECT COUNT(*)::int FROM measurements_test;")
    return {"inserted_id": int(row_id), "total_rows": int(total)}

# rota alternativa para conferir arquivo estático (caso queira)
@app.get("/static-check", response_class=HTMLResponse)
async def static_check():
    fp = os.path.join(static_dir, "grafico.html")
    if not os.path.isfile(fp):
        return HTMLResponse("<h3>grafico.html não encontrado em static/</h3>", status_code=404)
    with open(fp, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
