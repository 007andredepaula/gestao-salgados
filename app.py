import streamlit as st
import sqlite3
import pandas as pd
import uuid
import secrets
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestão Integrada - Fábrica de Salgados", layout="wide")

# --- CONEXÃO COM BANCO DE DADOS ---
def criar_conexao():
    conn = sqlite3.connect('gestao_integrada.db', check_same_thread=False)
    return conn

def inicializar_banco():
    conn = criar_conexao()
    cursor = conn.cursor()
    
    # Tabela de Unidades Regionais (Cidades e Metas)
    cursor.execute('''CREATE TABLE IF NOT EXISTS regionais (
        id INTEGER PRIMARY KEY, cidade TEXT, meta_mensal REAL)''')
    
    # Tabela de Dispositivos Autorizados (Segurança MAC/Fingerprint)
    cursor.execute('''CREATE TABLE IF NOT EXISTS dispositivos_autorizados (
        device_id TEXT PRIMARY KEY, loja_id INTEGER, aprovado BOOLEAN)''')
    
    # Tabela de Tokens de Uso Único
    cursor.execute('''CREATE TABLE IF NOT EXISTS tokens_acesso (
        token TEXT PRIMARY KEY, loja_id INTEGER, status TEXT, expiracao TIMESTAMP)''')
    
    # Tabela de Vendas e Faturamento
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY, loja_id INTEGER, valor REAL, data TIMESTAMP, cidade TEXT)''')

    # Tabela de Funcionários e Bônus
    cursor.execute('''CREATE TABLE IF NOT EXISTS funcionarios (
        id INTEGER PRIMARY KEY, nome TEXT, cargo TEXT, loja_id INTEGER, cidade TEXT, salario_base REAL)''')

    # Inserir dados iniciais de teste se vazio
    cursor.execute("SELECT count(*) FROM regionais")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO regionais (cidade, meta_mensal) VALUES ('Guarapari', 100000.0)")
    
    conn.commit()
    conn.close()

inicializar_banco()

# --- LÓGICA DE SEGURANÇA ---
def get_device_id():
    # Gera um ID persistente para o navegador (Simulação de Hardware Fingerprint)
    if 'device_id' not in st.session_state:
        st.session_state.device_id = str(uuid.getnode())
    return st.session_state.device_id

def verificar_acesso():
    dev_id = get_device_id()
    conn = criar_conexao()
    cursor = conn.cursor()
    cursor.execute("SELECT aprovado FROM dispositivos_autorizados WHERE device_id = ? AND aprovado = 1", (dev_id,))
    autorizado = cursor.fetchone()
    conn.close()
    return autorizado is not None

# --- INTERFACE PRINCIPAL ---

# Menu Lateral de Navegação
st.sidebar.title("🥨 Gestão de Fábrica")
perfil = st.sidebar.selectbox("Acesso", ["Funcionário", "Gerente", "Administrador"])

# Verificação de Dispositivo para Funcionários e Gerentes
if perfil in ["Funcionário", "Gerente"]:
    if not verificar_acesso():
        st.error("🚨 Dispositivo não autorizado. Solicite o link de acesso único ao Administrador.")
        st.stop()

# --- ABA ADMINISTRADOR (DONO) ---
if perfil == "Administrador":
    st.title("🏛️ Painel do Administrador Geral")
    
    tab1, tab2, tab3 = st.tabs(["Segurança e Dispositivos", "Metas Regionais", "Financeiro & Bônus"])
    
    with tab1:
        st.subheader("Gerar Link de Acesso Único")
        loja_alvo = st.number_input("ID da Loja", min_value=1, max_value=10, step=1)
        if st.button("Gerar Novo Link"):
            token = secrets.token_urlsafe(16)
            # Salvar token no banco (Lógica de uso único)
            st.success(f"Envie este link ao Gerente: `https://seu-sistema.streamlit.app/?token={token}`")
            
        st.divider()
        st.subheader("Aprovações Pendentes")
        # Aqui apareceriam os dispositivos que usaram o link
        st.info("Nenhuma solicitação pendente no momento.")

    with tab2:
        st.subheader("Configuração de Metas por Cidade")
        cidade = st.selectbox("Cidade", ["Guarapari", "Anchieta", "Vila Velha", "Vitória"])
        nova_meta = st.number_input("Meta Mensal (R$)", value=100000.0)
        if st.button("Atualizar Meta"):
            st.success(f"Meta de {cidade} atualizada para R$ {nova_meta}")

# --- ABA OPERACIONAL (CAIXA) ---
if perfil == "Funcionário":
    st.title("🛒 Frente de Caixa")
    st.write("Bipe o produto ou selecione o combo:")
    
    codigo_barras = st.text_input("Aguardando Leitura do Código...")
    if codigo_barras:
        st.write(f"✅ Produto {codigo_barras} adicionado ao carrinho.")
        # Lógica de baixa automática no SQLite
        
    if st.button("Finalizar Venda"):
        st.balloons()
        st.success("Venda registrada! Estoque atualizado.")

# --- ABA GERENTE (LOGÍSTICA E EQUIPE) ---
if perfil == "Gerente":
    st.title("📊 Gestão da Unidade")
    
    st.subheader("🚚 Monitoramento de Logística")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Motoboy 01", "Online", delta="Em trânsito")
    with col2:
        st.warning("⚠️ Alerta: Veículo parado há 12 min em Guarapari!")
        
    st.subheader("💰 Bônus de Equipe (Trava de Meta)")
    # Simulação da trava de meta regional
    faturamento_atual = 85000.0
    meta_regional = 100000.0
    progresso = faturamento_atual / meta_regional
    
    st.progress(progresso)
    st.write(f"Faturamento da Cidade: R$ {faturamento_atual} / R$ {meta_regional}")
    
    if faturamento_atual < meta_regional:
        st.error("🚫 Meta Regional não atingida. Bônus de equipe bloqueado.")
    else:
        st.success("✅ Meta Atingida! Bônus liberado para a folha de pagamento.")

# --- FOOTER DE STATUS ---
st.sidebar.divider()
st.sidebar.caption(f"Status do Dispositivo: {'🟢 Autorizado' if verificar_acesso() else '🔴 Bloqueado'}")
st.sidebar.caption(f"ID: {get_device_id()}")
