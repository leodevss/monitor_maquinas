# agent/agent.py
import os, time, json, requests, psutil
from datetime import datetime
from pathlib import Path
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "minha-chave-teste")
CLIENT_ID = os.environ.get("CLIENT_ID", "pc-001")
INTERVAL = int(os.environ.get("INTERVALO_SEGUNDOS", "60"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5")) # agent checa comando a
cada 5s
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
BUFFER = DATA_DIR / "buffer.jsonl"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
def get_command():
try:
r = requests.get(f"{SERVER_URL}/api/command/{CLIENT_ID}", timeout=5)
r.raise_for_status()
return r.json().get("command", "stop")
except Exception as e:
print("Erro ao buscar comando:", e)
return "stop"
def send_payload(payload):
try:
r = requests.post(f"{SERVER_URL}/api/collect", json=payload, headers=HEADERS,
timeout=8)
r.raise_for_status()
return True
except Exception as e:
print("Falha ao enviar payload:", e)
return False
def flush_buffer():
if not BUFFER.exists():
return
lines = BUFFER.read_text().strip().splitlines()
remaining = []
for l in lines:
p = json.loads(l)
if not send_payload(p):
remaining.append(l)
else:
print("Buffered record flushed")
if remaining:
BUFFER.write_text("\n".join(remaining))
else:
try:
BUFFER.unlink()
except:
pass
def collect_once_and_send():
payload = {
"client_id": CLIENT_ID,
"timestamp": datetime.utcnow().isoformat(),
"cpu": psutil.cpu_percent(interval=1),
"ram": psutil.virtual_memory().percent
}
if not send_payload(payload):
# append to buffer
with open(BUFFER, "a", encoding="utf-8") as f:
f.write(json.dumps(payload) + "\n")
def run_agent():
active = False
next_collect_at = 0
while True:
cmd = get_command()
if cmd == "start":
if not active:
print("START command received - starting collection")
active = True
next_collect_at = time.time()
# collect when time
if active and time.time() >= next_collect_at:
collect_once_and_send()
flush_buffer()
next_collect_at = time.time() + INTERVAL
else:
if active:
print("STOP command received - stopping collection and flushing buffer")
# flush remaining
flush_buffer()
active = False
time.sleep(POLL_INTERVAL)
if __name__ == "__main__":
run_agent()

