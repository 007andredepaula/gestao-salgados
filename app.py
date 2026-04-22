import streamlit as st
import sqlite3
import pandas as pd
import uuid
import secrets
from datetime import datetime, timedelta
import urllib.parse

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema de Gestão Multicidades", layout="wide")
ADMIN_USER = "admin"
ADMIN_PASS = "salgados2026" 

# --- BANCO DE DADOS ---
def criar_conexao():
    return sqlite3.connect('gestao_integrada.db', check_same_thread=False)

def inicializar_banco():
    conn = criar_conexao(); cursor = conn.cursor()
    # Tabela de dispositivos agora inclui CIDADE e NIVEL
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
    cursor.execute("SELECT aprovado, loja_id, nivel, cidade FROM dispositivos_autorizados WHERE device_id = ? AND aprovado = 1", (get_device_id(),))
    res = cursor.fetchone(); conn.close()
    return res # (aprovado, loja_id, nivel, cidade)

# --- CAPTURA DE TOKEN ---
qp = st.query_params
if "token" in qp:
    conn = criar_conexao(); cursor = conn.cursor()
    cursor.execute("SELECT loja_id, nivel, cidade FROM tokens_acesso WHERE token = ? AND status = 'pendente'", (qp["token"],))
    res = cursor.fetchone()
    if res:
        cursor.execute("INSERT OR REPLACE INTO dispositivos_autorizados VALUES (?, ?, ?, ?, 0)", (get_device_id(), res[0], res[1], res[2]))
        cursor.execute("UPDATE tokens_acesso SET status = 'utilizado' WHERE token = ?", (qp["token"],))
        conn.commit(); st.success("✅ Dispositivo registrado! Aguarde aprovação.")
    conn.close()

# --- INTERFACE ---
acesso = verificar_acesso()
st.sidebar.title("🥨 Gestão Integrada")

if not acesso:
    perfil_selecionado = st.sidebar.selectbox("Acesso", ["Login Admin", "Aguardando Liberação"])
else:
    # Trava de Segurança por Dispositivo
    status, loja_id, nivel, cidade_user = acesso
    st.sidebar.info(f"📍 {cidade_user} | {nivel}")
    
    if nivel == "Funcionário": perfil_selecionado = "Funcionário"
    elif nivel == "Gerente": perfil_selecionado = st.sidebar.selectbox("Mudar Para", ["Gerente", "Funcionário"])
    elif nivel == "Fábrica": perfil_selecionado = "Fábrica"
    else: perfil_selecionado = st.sidebar.selectbox("Admin", ["Administrador", "Fábrica", "Gerente", "Funcionário"])

# --- TELAS ---

if perfil_selecionado == "Login Admin" or perfil_selecionado == "Administrador":
    st.title("🏛️ Painel Administrativo Geral")
    if 'auth' not in st.session_state: st.session_state['auth'] = False
    if not st.session_state['auth']:
        u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u == ADMIN_USER and p == ADMIN_PASS: st.session_state['auth'] = True; st.rerun()
        st.stop()

    tab1, tab2 = st.tabs(["Gerar Links", "Aprovações"])
    with tab1:
        col = st.columns(3)
        l_id = col[0].number_input("ID Loja", 1, 50, 1)
        cid = col[1].selectbox("Cidade", ["Guarapari", "Vitoria", "Vila Velha"])
        niv = col[2].selectbox("Nível", ["Funcionário", "Gerente", "Fábrica"])
        if st.button("Criar Link de Acesso"):
            tk = secrets.token_urlsafe(16)
            conn = criar_conexao(); cursor = conn.cursor()
            cursor.execute("INSERT INTO tokens_acesso VALUES (?, ?, ?, ?, 'pendente', ?)", (tk, l_id, niv, cid, datetime.now()+timedelta(hours=24)))
            conn.commit(); conn.close()
            st.code(f"https://sistema-gestao.streamlit.app/?token={tk}")

elif perfil_selecionado == "Fábrica":
    st.title(f"🏭 Painel de Produção - {cidade_user}")
    st.subheader("Enviar Salgados para Lojas")
    # A fábrica só vê lojas da mesma cidade
    loja_dest = st.number_input("ID da Loja Destino", 1, 50, 1)
    prod = st.selectbox("Salgado", ["Cento de Coxinha", "Cento de Kibe", "Empada"])
    qtd = st.number_input("Quantidade", 1, 1000, 100)
    
    if st.button("Confirmar Envio"):
        conn = criar_conexao(); cursor = conn.cursor()
        cursor.execute("INSERT INTO estoque (loja_id, cidade, produto, quantidade) VALUES (?, ?, ?, ?)", (loja_dest, cidade_user, prod, qtd))
        conn.commit(); conn.close()
        st.success(f"Enviado para Loja {loja_dest} em {cidade_user}!")

elif perfil_selecionado == "Funcionário":
    st.title(f"🛒 Balcão - Loja {loja_id} ({cidade_user})")
    v_prod = st.selectbox("Venda", ["Cento de Coxinha", "Cento de Kibe", "Empada"])
    v_qtd = st.number_input("Qtd", 1, 50, 1)
    if st.button("Vender"):
        st.success("Venda realizada!")
