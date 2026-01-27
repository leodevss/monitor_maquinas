Sistema de Monitoramento Distribuído de Recursos de Hardware
1. Visão Geral do Projeto
Este projeto consiste em uma solução de arquitetura Cliente-Servidor para o monitoramento em tempo real da saúde de hardware (CPU e Memória RAM) de múltiplas estações de trabalho. Diferente de monitoramentos locais, este sistema utiliza um banco de dados PostgreSQL na Nuvem como intermediário, permitindo que a coleta e a visualização ocorram através da internet, sem necessidade de VPNs ou configurações complexas de rede.

2. Arquitetura Técnica
A solução opera de forma desacoplada em dois módulos principais:

O Agente (Client-Side): Script Python que roda nas máquinas alvo. Ele coleta métricas a cada segundo usando a biblioteca psutil. Possui arquitetura "Offline-First", gravando dados em um buffer local (SQLite) antes de enviar para a nuvem, garantindo que nenhum dado seja perdido em caso de queda de internet.

O Dashboard (Server-Side): Aplicação web desenvolvida em Streamlit. Ela consome os dados da nuvem e exibe gráficos interativos (Plotly), permitindo análise de tendências através de Média Móvel Exponencial (EMA) e controle remoto (Início/Parada) da coleta.

3. Funcionalidades Principais
Coleta em Tempo Real: Monitoramento contínuo de CPU e RAM.

Segurança de Dados: Buffer local para contingência (sem perda de dados).

Controle Remoto: Inicie ou pare a coleta de todos os agentes através do painel web.

Análise Avançada: Gráficos com Zoom, seleção de horário específico e comparação entre múltiplas máquinas.

4. Tecnologias Utilizadas
Linguagem: Python 3.12+

Frontend: Streamlit

Banco de Dados: PostgreSQL (Nuvem/Neon) e SQLite (Local).

Bibliotecas: Psutil, Plotly Express, Psycopg2, Pandas, Python-Dotenv.

🚀 Guia de Instalação e Execução
Siga este roteiro para rodar o projeto do zero.

Pré-requisitos
Python instalado (versão 3.10 ou superior).

Git instalado.

URL de conexão com o Banco de Dados PostgreSQL.

Passo 1: Clonar e Configurar
Baixe o projeto ou clone o repositório:

Bash

git clone https://github.com/SEU_USUARIO/NOME_DO_PROJETO.git
cd NOME_DO_PROJETO
Crie um arquivo chamado .env na raiz do projeto e adicione sua senha do banco:

Snippet de código

DATABASE_URL=postgresql://seu_usuario:sua_senha@host_do_banco/nome_db?sslmode=require
Passo 2: Criar Ambiente Virtual (Recomendado)
Para não misturar as bibliotecas, crie um ambiente isolado.

No Windows:

Bash

python -m venv venv
.\venv\Scripts\Activate
No Linux/Mac:

Bash

python3 -m venv venv
source venv/bin/activate
Passo 3: Instalar Dependências
Com o ambiente ativado (aparecerá (venv) no terminal), instale as ferramentas necessárias:

Bash

pip install -r requirements.txt
🧪 Como Rodar e Testar (Passo a Passo)
O sistema precisa de dois terminais abertos simultaneamente: um para o Site (Servidor) e outro para o Agente (Máquina Monitorada).

1. Iniciar o Painel de Controle (Terminal 1)
No primeiro terminal, execute:

Bash

streamlit run server/main.py
O navegador abrirá automaticamente exibindo o Dashboard.

Verifique se o status no topo está "OFFLINE" ou "ONLINE".

2. Iniciar o Agente Coletor (Terminal 2)
Abra um novo terminal, ative o venv novamente e execute:

Bash

python agent/agent.py
Você verá a mensagem: 🤖 Agente ligado e aguardando comando do site... ou zzz... Aguardando....

3. Realizar o Teste de Funcionamento
Agora vamos fazer a mágica acontecer:

Vá até o navegador (Dashboard).

Clique no botão ▶️ INICIAR.

Observe o Terminal 2 (Agente): Ele deve mudar imediatamente para 🟢 MONITORANDO: [Nome-do-PC]....

Volte ao navegador e clique em 🔄 Atualizar.

Os gráficos começarão a ser desenhados. Teste os filtros de data e a barra de zoom abaixo dos gráficos.

Para finalizar, clique em ⏹️ PARAR no site e veja o agente voltar a dormir no terminal.
