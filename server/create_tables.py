import psycopg2

def create_tables():
    print("⏳ Configurando Banco de Dados...")
    
    # SUA SENHA DIRETA
    url = "postgresql://neondb_owner:npg_uZgUDyn5L9tj@ep-jolly-block-acb0ntqm-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

    try:
        conn = psycopg2.connect(url)
        cursor = conn.cursor()
        
        # 1. Tabela de Monitoramento (Dados)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitoramento (
            id SERIAL PRIMARY KEY,
            hostname VARCHAR(100),
            data_hora TIMESTAMP,
            uso_cpu FLOAT,
            uso_ram FLOAT
        );
        """)

        # 2. Tabela de Controle (Botão Ligar/Desligar)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS controle_remoto (
            id INT PRIMARY KEY,
            comando VARCHAR(20)
        );
        """)
        
        # Insere o comando inicial 'PARAR' se a tabela estiver vazia
        cursor.execute("INSERT INTO controle_remoto (id, comando) VALUES (1, 'PARAR') ON CONFLICT (id) DO NOTHING;")
        
        conn.commit()
        print("✅ SUCESSO! Tabelas e Controle Remoto configurados.")
        conn.close()
        
    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    create_tables()