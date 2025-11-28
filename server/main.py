import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# load .env in local/dev (Render ignores this and uses env vars configured in dashboard)
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitor_server")

DATABASE_URL = os.getenv("DATABASE_URL") # expected: postgresql://user:pass@host:5432/dbname
API_KEY = os.getenv("API_KEY") # optional, if you want to protect agent ingestion

if not DATABASE_URL:
# In deploy we want this to fail loud so you set env var in Render
logger.error("DATABASE_URL não configurada (env var).")
# do not raise here if you want app to start but we prefer to raise so Render build shows error
raise RuntimeError("DATABASE_URL não configurada (env var)")

# ---------- DB helpers ----------
def get_conn():
# For Supabase require sslmode=require occasionally required
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
return conn

def init_db():
"""Cria tabela se não existir."""
sql = """
CREATE TABLE IF NOT EXISTS metricas (
id SERIAL PRIMARY KEY,
data_hora TIMESTAMP NOT NULL,
cpu REAL NOT NULL,
ram REAL NOT NULL
);
"""
conn = get_conn()
try:
cur = conn.cursor()
cur.execute(sql)
conn.commit()
cur.close()
logger.info("Tabela metricas garantida.")
finally:
conn.close()

def insert_batch(rows: List[tuple]):
"""
rows: list of (datetime, cpu, ram) where datetime is a python datetime or string
"""
if not rows:
return 0
conn = get_conn()
try:
cur = conn.cursor()
execute_values(
cur,
"INSERT INTO metricas (data_hora, cpu, ram) VALUES %s",
rows
)
conn.commit()
count = cur.rowcount
cur.close()
logger.info(f"{len(rows)} registros inseridos.")
return len(rows)
finally:
conn.close()

def query_latest(limit: int = 100):
conn = get_conn()
try:
cur = conn.cursor()
cur.execute(
"SELECT id, data_hora, cpu, ram FROM metricas ORDER BY data_hora DESC LIMIT %s",
(limit,)
)
rows = cur.fetchall()
cur.close()
return rows
finally:
conn.close()

# ---------- Pydantic models ----------
class Medicao(BaseModel):
data_hora: str # "YYYY-MM-DD HH:MM:SS" or ISO
cpu: float
ram: float

@validator("data_hora")
def parse_dt(cls, v):
# Accept common formats; keep as string here and parse later
try:
# try ISO first
datetime.fromisoformat(v)
except Exception:
# try fallback
try:
datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
except Exception:
raise ValueError("Formato data_hora inválido. Use ISO ou 'YYYY-MM-DD HH:MM:SS'")
return v

class BatchIn(BaseModel):
measurements: List[Medicao]
api_key: Optional[str] = None

# ---------- App ----------
app = FastAPI(title="Monitor de Recursos - Server")

# serve static files from ./static at /static
HERE = Path(__file__).parent
STATIC_DIR = HERE / "static"
if not STATIC_DIR.exists():
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# init DB on startup
@app.on_event("startup")
def on_startup():
logger.info("Inicializando DB...")
init_db()
logger.info("Startup completo.")

# Health
@app.get("/health")
def health():
return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# Ingest endpoint - agent posts a batch of measurements
@app.post("/ingest", status_code=201)
def ingest(data: BatchIn, request: Request):
# optional API key check
if API_KEY:
# prefer header X-API-KEY or data.api_key
key_header = request.headers.get("x-api-key")
provided = key_header or data.api_key
if provided != API_KEY:
raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key inválida")

rows = []
for m in data.measurements:
# parse datetime into python datetime
try:
dt = None
try:
dt = datetime.fromisoformat(m.data_hora)
except Exception:
dt = datetime.strptime(m.data_hora, "%Y-%m-%d %H:%M:%S")
rows.append((dt, float(m.cpu), float(m.ram)))
except Exception as e:
raise HTTPException(status_code=400, detail=f"Erro ao parsear medicao: {e}")

try:
inserted = insert_batch(rows)
return {"inserted": inserted}
except Exception as e:
logger.exception("Erro ao inserir lote")
raise HTTPException(status_code=500, detail=str(e))

# Get latest measurements (for UI)
@app.get("/api/latest")
def api_latest(limit: int = 100):
try:
rows = query_latest(limit)
# rows are in desc order; we can reverse to ascending for plotting
result = [
{"id": r[0], "data_hora": r[1].isoformat(), "cpu": float(r[2]), "ram": float(r[3])}
for r in reversed(rows)
]
return {"count": len(result), "data": result}
except Exception as e:
logger.exception("Erro ao consultar latest")
raise HTTPException(status_code=500, detail=str(e))

# Convenience: serve index or grafico
@app.get("/")
def index():
index_file = STATIC_DIR / "control.html"
if index_file.exists():
return FileResponse(index_file)
return {"message": "Coloque control.html em /server/static e recarregue."}

# small endpoint to test DB connectivity quickly
@app.get("/db-test")
def db_test():
try:
rows = query_latest(1)
return {"ok": True, "sample_count": len(rows)}
except Exception as e:
logger.exception("DB test falhou")
raise HTTPException(status_code=500, detail=f"
