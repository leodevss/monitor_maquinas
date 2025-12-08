import psutil
import sqlite3
import time
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

# --- CONFIGURAÇÕES ---
INTERVALO_CHECAGEM = 2  # Verifica o comando a cada 2s
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# Banco Local
DB_LOCAL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'buffer.db')
os.makedirs(os.path.dirname(DB_LOCAL_PATH), exist_ok=True)

def init_local_db():
    conn = sqlite3.connect(DB_LOCAL_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS metricas (id INTEGER PRIMARY KEY, hostname TEXT, data_hora TEXT, cpu_uso REAL, ram_uso REAL)')
    conn.commit()
    conn.close()

def verificar_permissao():
    """Pergunta ao servidor se pode coletar"""
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT comando FROM controle_remoto WHERE id=1")
        resultado = cursor.fetchone()
        conn.close()
        if resultado and resultado[0] == 'INICIAR':
            return True
        return False
    except:
        return False # Se der erro na internet, para por segurança

def trabalhar_e_enviar():
    # 1. Coleta
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    hostname = os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'Unknown')
    agora = datetime.now().isoformat()

    print(f"🟢 MONITORANDO: {hostname} | CPU: {cpu}% | RAM: {ram}%")

    # 2. Envia DIRETO (Para ser rápido na apresentação)
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO monitoramento (hostname, data_hora, uso_cpu, uso_ram) VALUES (%s, %s, %s, %s)", 
                      (hostname, agora, cpu, ram))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Erro de envio: {e}")

if __name__ == "__main__":
    init_local_db()
    print("🤖 Agente ligado e aguardando comando do site...")
    
    while True:
        # Pergunta para o "Chefe" (Banco de dados) se pode trabalhar
        pode_coletar = verificar_permissao()
        
        if pode_coletar:
            trabalhar_e_enviar()
            time.sleep(2) # Coleta a cada 2 segundos se estiver ligado
        else:
            print("zzz... Aguardando 'Iniciar' no site...", end='\r')
            time.sleep(3)