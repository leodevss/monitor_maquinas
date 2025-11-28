# server/main.py
import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# carrega .env se existir (útil localmente)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # ex: postgresql://user:pass@host:5432/dbname
API_KEY = os.getenv("API_KEY", "")

if not DATABASE_URL:
    # levantamos logo, para o deploy falhar com mensagem óbvia
    raise RuntimeError("DATABASE_URL não configurada (env var) — defina DATABASE_URL no Render / .env")

# Força SSL para Supabase (caso a URL não contenha ?sslmode)
if "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL + "&sslmode=require"
    else:
        DATABASE_URL = DATABASE_URL + "?sslmode=require"

app = FastAPI(title="Monitor de Recursos Computacionais")

# Serve arquivos estáticos em /static (coloque grafico.html e control.html em server/static/)
app.mount("/static", StaticFiles(directory="server/static"), name="static")

executor = ThreadPoolExecutor(max_workers=2)

def sync_db_ping() -> Dict[str, Any]:
    """
    Função síncrona que testa conexão com o banco e retorna NOW().
    Executada em threadpool para não bloquear o loop async do FastAPI.
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT NOW() as now_time;")
        row = cur.fetchone()
        cur.close()
        return {"ok": True, "now": row["now_time"].isoformat()}
    finally:
        if conn:
            conn.close()

@app.get("/", response_class=HTMLResponse)
async def index():
    """
    Página inicial simples que redireciona/explica.
    Se você quiser abrir o controle: /static/control.html
    Para o gráfico: /static/grafico.html
    """
    html = f"""
    <html>
      <head><meta charset="utf-8"><title>Monitor de Recursos</title></head>
      <body style="font-family:Arial,Helvetica,sans-serif">
        <h2>Monitor de Recursos</h2>
        <p>Ruas rápidas:</p>
        <ul>
          <li><a href="/static/control.html" target="_blank">Tela Controle (control.html)</a></li>
          <li><a href="/static/grafico.html" target="_blank">Gráfico (grafico.html)</a></li>
          <li><a href="/api/db_ping">Testar conexão com o banco (API)</a></li>
        </ul>
        <small>Deploy time: {datetime.utcnow().isoformat()} UTC</small>
      </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/api/db_ping")
async def db_ping():
    """
    Endpoint para testar se o backend consegue conectar ao banco (Supabase).
    Útil no Render / mobile para confirmar que a variável DATABASE_URL foi aplicada.
    """
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(executor, sync_db_ping)
        return JSONResponse(result)
    except Exception as e:
        # devolve detalhe para debug (não exponha em produção sem sanitizar)
        raise HTTPException(status_code=500, detail=f"DB ping failed: {e}")

@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# --- exemplo de endpoint para receber medições (se quiser) ---
class Medicao(BaseModel):
    client_id: str
    timestamp: str  # isoformat
    cpu: float
    ram: float

@app.post("/api/medicao")
async def receber_medicao(m: Medicao):
    """
    Endpoint simples para aceitar uma medição. Por enquanto apenas retorna OK.
    No futuro você salva no banco (INSERT) aqui.
    """
    # Exemplo mínimo de validação
    if not m.client_id:
        raise HTTPException(status_code=400, detail="client_id missing")
    # TODO: salvar no banco (async/worker)
    return {"received": True, "client": m.client_id, "ts": m.timestamp}

# permite rodar localmente com python server/main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)

