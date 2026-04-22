import streamlit as st
import sqlite3
import pandas as pd
import uuid
import secrets
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema de Gestão Integrada", layout="wide")
ADMIN_USER = "admin"
ADMIN_PASS = "salgados2026" 

def criar_conexao():
    return sqlite3.connect('gestao_integrada.db', check_same_thread=False)

def inicializar_banco():
    conn = criar_conexao(); cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS dispositivos_autorizados (
        device_id TEXT PRIMARY KEY, loja_id INTEGER, nivel TEXT, cidade TEXT, aprovado BOOLEAN DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tokens_acesso (
        token TEXT PRIMARY KEY, loja_id INTEGER, nivel TEXT, cidade TEXT, status TEXT, expiracao TIMESTAMP)''')
    cursor.execute('CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY, loja_id INTEGER, cidade TEXT, produto TEXT, quantidade INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY, loja_id INTEGER, cidade TEXT, produto TEXT, valor REAL, quantidade INTEGER, data TIMESTAMP)')
    conn.commit(); conn.close()

inicializar_banco()
def get_device_id(): return str(uuid.getnode())

def verificar_acesso():
    conn = criar_conexao(); cursor = conn.cursor()
    cursor.execute("SELECT aprovado, loja_id, nivel, cidade FROM dispositivos_autorizados WHERE device_id = ?", (get_device_id(),))
    res = cursor.fetchone(); conn.close()
    return res 

# --- LÓGICA DE ACESSO ---
acesso = verificar_acesso()
st.sidebar.title("🥨 Gestão de Fábrica")

# 1. BLOQUEIO TOTAL PARA LOJAS
# Se o dispositivo for de Funcionário ou Gerente, ele NÃO PODE escolher ser Admin
if acesso and acesso[0] == 1:
    status, loja_id_atual, nivel_user, cidade_user = acesso
    st.sidebar.success(f"Dispositivo Autorizado")
    st.sidebar.info(f"📍 {cidade_user}")
    
    if nivel_user == "Funcionário":
        perfil_selecionado = "Funcionário"
        st.sidebar.write("📌 Perfil: Caixa")
    elif nivel_user == "Gerente":
        perfil_selecionado = st.sidebar.selectbox("Ir para:", ["Gerente", "Funcionário"])
    elif nivel_user == "Fábrica":
        perfil_selecionado = "Fábrica"
    else: # Perfil de Administrador (apenas nos seus computadores)
        perfil_selecionado = st.sidebar.selectbox("Painel Geral", ["Administrador", "Fábrica", "Gerente", "Funcionário"])
else:
    perfil_selecionado = st.sidebar.selectbox("Acesso", ["Aguardando Liberação", "Login Administrador"])

# --- ÁREA DO ADMINISTRADOR (CENTRAL DE COMANDO) ---
if perfil_selecionado == "Administrador" or perfil_selecionado == "Login Administrador":
    if 'auth' not in st.session_state: st.session_state['auth'] = False
    if not st.session_state['auth']:
        st.title("🔐 Login do Administrador")
        u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u == ADMIN_USER and p == ADMIN_PASS: st.session_state['auth'] = True; st.rerun()
        st.stop()

    st.title("🏛️ Painel do Administrador Geral")
    
    # ORGANIZAÇÃO POR CIDADE NA LATERAL DO ADMIN
    with st.sidebar.expander("🌍 Estrutura Guarapari", expanded=True):
        st.write("🏭 Fábrica Guarapari")
        st.write("👥 Gerentes: Loja 1, Loja 2")
        st.write("🛒 Caixas: Balcão 01, Balcão 02")

    tab1, tab2, tab3 = st.tabs(["Aprovações e Segurança", "Gestão de Lojas", "Relatórios Financeiros"])
    
    with tab1:
        st.subheader("Gerar Novos Acessos")
        c1, c2, c3 = st.columns(3)
        nova_loja = c1.number_input("ID Loja", 1, 10, 1)
        nova_cid = c2.selectbox("Cidade", ["Guarapari", "Vitoria"])
        novo_niv = c3.selectbox("Tipo de Link", ["Funcionário", "Gerente", "Fábrica"])
        if st.button("Gerar Link"):
            tk = secrets.token_urlsafe(16)
            conn = criar_conexao(); cursor = conn.cursor()
            cursor.execute("INSERT INTO tokens_acesso VALUES (?, ?, ?, ?, 'pendente', ?)", (tk, nova_loja, novo_niv, nova_cid, datetime.now()+timedelta(hours=24)))
            conn.commit(); conn.close()
            st.code(f"https://sistema-gestao.streamlit.app/?token={tk}")

        st.divider()
        st.subheader("Aprovações Pendentes")
        conn = criar_conexao(); cursor = conn.cursor()
        pendentes = pd.read_sql_query("SELECT * FROM dispositivos_autorizados WHERE aprovado = 0", conn)
        for _, r in pendentes.iterrows():
            if st.button(f"✅ Aprovar {r['nivel']} - Loja {r['loja_id']} ({r['cidade']})"):
                cursor.execute("UPDATE dispositivos_autorizados SET aprovado = 1 WHERE device_id = ?", (r['device_id'],))
                conn.commit(); conn.close(); st.rerun()
        conn.close()

# --- ÁREA DO FUNCIONÁRIO (TOTALMENTE RESTRITA) ---
elif perfil_selecionado == "Funcionário":
    st.title(f"🛒 Balcão de Vendas - Loja {loja_id_atual}")
    st.info(f"Unidade: {cidade_user} | Dispositivo: {get_device_id()[:8]}")
    
    with st.form("venda"):
        prod = st.selectbox("Salgado", ["Cento de Coxinha", "Cento de Kibe"])
        qtd = st.number_input("Quantidade", 1, 100, 1)
        if st.form_submit_button("Confirmar Venda"):
            st.success("Venda enviada para o administrador!")

# --- ÁREA DA FÁBRICA ---
elif perfil_selecionado == "Fábrica":
    st.title(f"🏭 Produção - {cidade_user}")
    st.write("Gerencie o envio de salgados para as lojas da sua região.")

elif perfil_selecionado == "Aguardando Liberação":
    st.title("⏳ Verificação Pendente")
    st.warning("Seu dispositivo ainda não foi aprovado pelo administrador.")
    if st.button("🔄 Atualizar Status"): st.rerun()
