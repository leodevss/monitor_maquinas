import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from datetime import date, datetime, time
import os
from dotenv import load_dotenv

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sistema de Monitoramento Distribuído", 
    layout="wide", 
    page_icon="🖥️"
)

# --- ESTILO CSS ---
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #d6d6d8;
    }
</style>
""", unsafe_allow_html=True)

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

# --- FUNÇÕES ---
def get_status():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT comando FROM controle_remoto WHERE id=1")
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else "DESCONHECIDO"
    except: return "ERRO"

def set_status(novo_status):
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        cursor.execute("UPDATE controle_remoto SET comando = %s WHERE id=1", (novo_status,))
        conn.commit()
        conn.close()
    except Exception as e: st.error(str(e))

def get_data(start_date, start_time, end_date, end_time, limite):
    try:
        conn = psycopg2.connect(DB_URL)
        timestamp_inicio = f"{start_date} {start_time}"
        timestamp_fim = f"{end_date} {end_time}"
        
        query = f"""
            SELECT hostname, data_hora, uso_cpu, uso_ram 
            FROM monitoramento 
            WHERE data_hora BETWEEN '{timestamp_inicio}' AND '{timestamp_fim}'
            ORDER BY data_hora DESC
        """
        if limite != "Todos":
            query += f" LIMIT {limite}"
            
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return pd.DataFrame()

# --- HEADER ---
st.title("🖥️ Monitoramento de Infraestrutura de TI")
status_atual = get_status()

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    if status_atual == 'INICIAR':
        st.metric("Status do Sistema", "ONLINE 🟢", "Coletando")
    else:
        st.metric("Status do Sistema", "OFFLINE 🔴", "Parado")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configurações")
st.sidebar.subheader("📅 Período")
datas = st.sidebar.date_input("Datas", [date.today(), date.today()])

st.sidebar.subheader("🕒 Horário")
col_h1, col_h2 = st.sidebar.columns(2)
with col_h1: hora_inicio = st.time_input("De:", time(0, 0))
with col_h2: hora_fim = st.time_input("Até:", time(23, 59))

st.sidebar.subheader("📊 Visualização")
limite_selecionado = st.sidebar.selectbox("Pontos no gráfico:", [100, 500, 1000, "Todos"], index=3) # Padrão 'Todos'

if st.sidebar.button("🔄 Atualizar", type="primary"):
    st.rerun()

# --- DASHBOARD ---
if len(datas) == 2:
    d_inicio, d_fim = datas
    df = get_data(d_inicio, hora_inicio, d_fim, hora_fim, limite_selecionado)

    if not df.empty:
        df['data_hora'] = pd.to_datetime(df['data_hora'])
        df = df.sort_values(by='data_hora', ascending=True)
        
        # Média Móvel
        df['EMA_CPU'] = df.groupby('hostname')['uso_cpu'].transform(lambda x: x.ewm(span=10).mean())
        df['EMA_RAM'] = df.groupby('hostname')['uso_ram'].transform(lambda x: x.ewm(span=10).mean())

        maquinas_unicas = df['hostname'].unique()
        with kpi2: st.metric("Máquinas Ativas", f"{len(maquinas_unicas)}", "No período")
        with kpi3: st.metric("Última Leitura", df['data_hora'].iloc[-1].strftime('%H:%M:%S'), "Horário")

        st.divider()
        c1, c2, _ = st.columns([1,1,3])
        with c1: 
            if st.button("▶️ INICIAR", use_container_width=True): set_status('INICIAR'); st.rerun()
        with c2: 
            if st.button("⏹️ PARAR", use_container_width=True): set_status('PARAR'); st.rerun()

        # Abas
        tab1, tab2 = st.tabs(["📈 Gráficos Interativos", "📋 Tabela de Dados"])

        with tab1:
            st.markdown(f"### Zoom Temporal ({hora_inicio} - {hora_fim})")
            selected_hosts = st.multiselect("Selecione as máquinas:", maquinas_unicas, default=maquinas_unicas)
            df_final = df[df['hostname'].isin(selected_hosts)]
            
            if not df_final.empty:
                # Melt para plotar bruto e média
                df_long_cpu = df_final.melt(id_vars=['data_hora', 'hostname'], value_vars=['uso_cpu', 'EMA_CPU'], 
                                            var_name='Tipo', value_name='Valor')
                df_long_ram = df_final.melt(id_vars=['data_hora', 'hostname'], value_vars=['uso_ram', 'EMA_RAM'], 
                                            var_name='Tipo', value_name='Valor')

                # --- GRÁFICO CPU ---
                st.info("📊 **Processador (CPU)** | Use a barra inferior para dar Zoom")
                fig_cpu = px.line(df_long_cpu, x='data_hora', y='Valor', color='hostname', line_dash='Tipo',
                                  height=500, title=None)
                
                # ATIVANDO O ZOOM E SLIDER
                fig_cpu.update_layout(hovermode="x unified")
                fig_cpu.update_xaxes(rangeslider_visible=True) # <--- AQUI ESTÁ O ZOOM
                
                st.plotly_chart(fig_cpu, use_container_width=True)

                st.markdown("---")

                # --- GRÁFICO RAM ---
                st.info("📊 **Memória (RAM)** | Use a barra inferior para dar Zoom")
                fig_ram = px.line(df_long_ram, x='data_hora', y='Valor', color='hostname', line_dash='Tipo',
                                  height=500, title=None)
                
                # ATIVANDO O ZOOM E SLIDER
                fig_ram.update_layout(hovermode="x unified")
                fig_ram.update_xaxes(rangeslider_visible=True) # <--- AQUI ESTÁ O ZOOM
                
                st.plotly_chart(fig_ram, use_container_width=True)
            else:
                st.warning("Selecione uma máquina.")

        with tab2:
            st.dataframe(df.sort_values(by='data_hora', ascending=False), use_container_width=True)

    else:
        st.warning(f"Sem dados no período.")