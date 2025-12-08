# 🖥️ Sistema de Monitoramento Distribuído

Sistema completo para monitoramento de recursos de hardware (CPU e RAM) em tempo real utilizando arquitetura Cliente-Servidor.

## 🚀 Funcionalidades

- **Coleta em Tempo Real:** Agente Python que monitora uso de CPU e Memória.
- **Buffer Local:** Armazenamento em SQLite para garantir dados mesmo sem internet (Offline-First).
- **Dashboard Web:** Interface em Streamlit com gráficos interativos e Média Móvel Exponencial (EMA).
- **Controle Remoto:** Inicie ou pare a coleta de dados de todas as máquinas remotamente.
- **Comparação:** Visualize e compare performance de múltiplas máquinas simultaneamente.

## 🛠️ Tecnologias

- **Python 3.12**
- **Streamlit** (Dashboard)
- **Plotly** (Gráficos Interativos)
- **PostgreSQL (Neon Tech)** (Banco na Nuvem)
- **SQLite** (Buffer Local)
- **Psutil** (Coleta de Hardware)

## 📦 Como rodar

1. Clone o repositório.
2. Crie um arquivo `.env` com a URL do seu banco PostgreSQL:
DATABASE_URL=sua_url_aqui

3. Instale as dependências:
```bash
pip install -r requirements.txt
Inicie o Servidor:

Bash

streamlit run server/main.py
Inicie o Agente (em outra máquina ou terminal):

Bash

python agent/agent.py