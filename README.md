
# Monitor de Recursos - Server + Agent

Este projeto monitora:
- CPU (%)
- RAM (%)
- Timestamp
- Hostname (ID do cliente)

## Componentes

### 🟦 Server (FastAPI)
- Recebe medições dos agentes
- Salva no PostgreSQL (Supabase)
- Envia comandos START/STOP
- Serve páginas HTML de controle

### 🟩 Agent
- Roda no computador cliente
- Coleta CPU/RAM
- Envia para o Server
- Guarda buffer offline quando o server cai
- Obedece comandos remotos
