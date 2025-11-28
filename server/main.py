import os
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv() # carrega DATABASE_URL e API_KEY de .env

DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY", None) # opcional: se definido, protege operações administrativas

if not DATABASE_URL:
raise RuntimeError("DATABASE_URL não configurada (env var)")

app = FastAPI(title="Monitor Collector API")

# serve arquivos estáticos em server/static (control.html, grafico.html, etc.)
app.mount("/static", StaticFiles(directory="server/static"), name="static")


# ---------- utilitários ----------
def get_conn():
"""Retorna conexão psycopg2 (não esquecer de fechar)."""
return psycopg2.connect(DATABASE_URL)


def init_db():
"""Cria tabelas necessárias caso não existam."""
conn = get_conn()
cur = conn.cursor()
cur.execute(
"""
CREATE TABLE IF NOT EXISTS metricas (
id SERIAL PRIMARY KEY,
hostname TEXT NOT NULL,
ts TIMESTAMP NOT NULL,
cpu REAL NOT NULL,
ram REAL NOT NULL
);
"""
)
cur.execute(
"""
CREATE TABLE IF NOT EXISTS comandos (
client_id TEXT PRIMARY KEY,
command TEXT,
updated_at TIMESTAMP
);
"""
)
conn.commit()
cur.close()
conn.close()


@app.on_event("startup")
def startup_event():
init_db()


# ---------- modelos ----------
class CollectPayload(BaseModel):
hostname: str
timestamp: Optional[str] = None # ISO string; se ausente, servidor usa NOW()
cpu: float
ram: float


# ---------- endpoints principais ----------
@app.post("/api/collect")
def collect(payload: CollectPayload):
"""
Recebe medições do agent.
payload.timestamp pode ser ISO string; se inválido/ausente usamos NOW().
"""
ts = None
if payload.timestamp:
try:
ts = datetime.fromisoformat(payload.timestamp)
except Exception:
ts = None

conn = get_conn()
cur = conn.cursor()
if ts:
cur.execute(
"INSERT INTO metricas (hostname, ts, cpu, ram) VALUES (%s, %s, %s, %s)",
(payload.hostname, ts, payload.cpu, payload.ram),
)
else:
# usa NOW() no SQL se timestamp inválido/ausente
cur.execute(
"INSERT INTO metricas (hostname, ts, cpu, ram) VALUES (%s, NOW(), %s, %s)",
(payload.hostname, payload.cpu, payload.ram),
)
conn.commit()
cur.close()
conn.close()
return {"status": "ok"}


@app.get("/api/metrics")
def get_metrics(hostname: Optional[str] = None, limit: int = 30):
"""
Retorna medições (JSON) ordenadas do mais antigo ao mais recente:
/api/metrics?hostname=pc-01&limit=50
"""
# defensiva: limitar tamanho máximo
try:
limit = int(limit)
except Exception:
limit = 30
if limit <= 0:
limit = 30
if limit > 1000:
limit = 1000

conn = get_conn()
cur = conn.cursor(cursor_factory=RealDictCursor)

if hostname:
cur.execute(
"""
SELECT ts as timestamp, cpu, ram
FROM metricas
WHERE hostname = %s
ORDER BY ts DESC
LIMIT %s
""",
(hostname, limit),
)
else:
cur.execute(
"""
SELECT ts as timestamp, cpu, ram
FROM metricas
ORDER BY ts DESC
LIMIT %s
""",
(limit,),
)

rows = cur.fetchall()
cur.close()
conn.close()

# rows já em desc order; queremos enviar do mais antigo ao mais recente para o frontend
rows.reverse()
# converte timestamp para ISO string (se for datetime)
for r in rows:
if isinstance(r["timestamp"], datetime):
r["timestamp"] = r["timestamp"].isoformat()
return JSONResponse(content=rows)


@app.get("/api/hosts")
def get_hosts():
"""Retorna lista com hostnames únicos (para popular o dropdown)."""
conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT DISTINCT hostname FROM metricas ORDER BY hostname")
rows = cur.fetchall()
cur.close()
conn.close()
hosts = [r[0] for r in rows]
return JSONResponse(content=hosts)


# ---------- comandos remotos ----------
@app.get("/api/command/{client_id}")
def get_command(client_id: str):
"""Agent consulta este endpoint para saber se deve iniciar/parar."""
conn = get_conn()
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("SELECT command, updated_at FROM comandos WHERE client_id = %s", (client_id,))
row = cur.fetchone()
cur.close()
conn.close()
if not row:
# por padrão, instruímos 'start' (ou poderia ser 'stop' conforme sua arquitetura)
return {"command": "start"}
return {"command": row["command"], "updated_at": (row["updated_at"].isoformat() if row["updated_at"] else None)}


@app.post("/api/command/{client_id}")
def set_command(client_id: str, request: Request, authorization: Optional[str] = Header(None)):
"""
Admin envia comando start/stop para um client_id.
Se API_KEY estiver definida, espera header: Authorization: Bearer <API_KEY>
"""
# validar API key se existir
if API_KEY:
if not authorization or API_KEY not in authorization:
raise HTTPException(status_code=401, detail="Unauthorized")

form = None
try:
form = await_request_json_or_form(request)
except Exception:
raise HTTPException(status_code=400, detail="Invalid payload")

# aceita payload JSON {"command":"start"} ou form-data
cmd = None
if isinstance(form, dict):
cmd = form.get("command")
else:
cmd = None

if cmd not in ("start", "stop"):
raise HTTPException(status_code=400, detail="Invalid command. Use 'start' or 'stop'.")

conn = get_conn()
cur = conn.cursor()
cur.execute(
"""
INSERT INTO comandos (client_id, command, updated_at)
VALUES (%s, %s, NOW())
ON CONFLICT (client_id) DO UPDATE SET command = EXCLUDED.command, updated_at = EXCLUDED.updated_at
""",
(client_id, cmd),
)
conn.commit()
cur.close()
conn.close()
return {"status": "ok", "client_id": client_id, "command": cmd}


# pequeno helper para aceitar json ou form-data
async def await_request_json_or_form(request: Request):
"""
Retorna dict com conteúdo:
- tenta JSON primeiro, se falhar tenta form data (multipart/form-data or x-www-form-urlencoded)
"""
try:
return await request.json()
except Exception:
try:
form = await request.form()
return dict(form)
except Exception:
return {}


# ---------- rotas para UI estático ----------
@app.get("/", response_class=HTMLResponse)
def index():
return {"status": "monitor-server ok"}


@app.get("/control", response_class=HTMLResponse)
def control_page():
# serve server/static/control.html
try:
with open("server/static/control.html", "r", encoding="utf-8") as f:
return HTMLResponse(f.read())
except FileNotFoundError:
return HTMLResponse("<h3>control.html não encontrado</h3>", status_code=404)


@app.get("/grafico", response_class=HTMLResponse)
def grafico_page():
try:
with open("server/static/grafico.html", "r", encoding="utf-8") as f:
return HTMLResponse(f.read())
except FileNotFoundError:
return HTMLResponse("<h3>grafico.html não encontrado</h3>", status_code=404)
