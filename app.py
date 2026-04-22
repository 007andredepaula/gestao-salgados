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
    return res # (aprovado, loja_id, nivel, cidade)

# --- CAPTURA DE TOKEN (O que o funcionário usa) ---
qp = st.query_params
if "token" in qp:
    token_val = qp["token"]
    conn = criar_conexao(); cursor = conn.cursor()
    cursor.execute("SELECT loja_id, nivel, cidade FROM tokens_acesso WHERE token = ? AND status = 'pendente'", (token_val,))
    res = cursor.fetchone()
    if res:
        # Registra o aparelho mas deixa APROVADO = 0 (esperando o admin)
        cursor.execute("INSERT OR REPLACE INTO dispositivos_autorizados VALUES (?, ?, ?, ?, 0)", (get_device_id(), res[0], res[1], res[2]))
        cursor.execute("UPDATE tokens_acesso SET status = 'utilizado' WHERE token = ?", (token_val,))
        conn.commit()
        st.success("✅ Solicitação enviada! Peça ao Administrador para aprovar este aparelho.")
    conn.close()

# --- INTERFACE ---
acesso = verificar_acesso()
st.sidebar.title("🥨 Gestão Integrada")

# Definir o que aparece no menu lateral
if not acesso or acesso[0] == 0:
    perfil_selecionado = st.sidebar.selectbox("Acesso", ["Aguardando Liberação", "Login Administrador"])
else:
    status, loja_id, nivel, cidade_user = acesso
    st.sidebar.success(f"Dispositivo Autorizado")
    st.sidebar.info(f"📍 {cidade_user} | {nivel}")
    
    if nivel == "Funcionário": 
        perfil_selecionado = "Funcionário"
    elif nivel == "Gerente": 
        perfil_selecionado = st.sidebar.selectbox("Menu", ["Gerente", "Funcionário"])
    elif nivel == "Fábrica": 
        perfil_selecionado = "Fábrica"
    else: 
        perfil_selecionado = st.sidebar.selectbox("Menu", ["Administrador", "Fábrica", "Gerente", "Funcionário"])

# --- TELA ADMINISTRADOR ---
if perfil_selecionado == "Login Administrador" or perfil_selecionado == "Administrador":
    if 'auth' not in st.session_state: st.session_state['auth'] = False
    
    if not st.session_state['auth']:
        st.title("🔐 Acesso Reservado")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Acessar Painel"):
            if u == ADMIN_USER and p == ADMIN_PASS:
                st.session_state['auth'] = True
                st.rerun()
            else: st.error("Incorreto")
        st.stop()

    st.title("🏛️ Painel do Administrador Geral")
    t1, t2, t3 = st.tabs(["Segurança e Aprovações", "Fábrica e Lojas", "Relatórios"])
    
    with t1:
        st.subheader("1. Gerar Link de Convite")
        c1, c2, c3 = st.columns(3)
        l_id = c1.number_input("ID Loja", 1, 50, 1)
        cid = c2.selectbox("Cidade", ["Guarapari", "Vitoria", "Vila Velha"])
        niv = c3.selectbox("Nível", ["Funcionário", "Gerente", "Fábrica"])
        if st.button("Gerar Link"):
            tk = secrets.token_urlsafe(16)
            conn = criar_conexao(); cursor = conn.cursor()
            cursor.execute("INSERT INTO tokens_acesso VALUES (?, ?, ?, ?, 'pendente', ?)", (tk, l_id, niv, cid, datetime.now()+timedelta(hours=24)))
            conn.commit(); conn.close()
            st.code(f"https://sistema-gestao.streamlit.app/?token={tk}")

        st.divider()
        st.subheader("2. Aprovações Pendentes")
        conn = criar_conexao(); cursor = conn.cursor()
        pendentes = pd.read_sql_query("SELECT device_id, nivel, loja_id, cidade FROM dispositivos_autorizados WHERE aprovado = 0", conn)
        if not pendentes.empty:
            for _, r in pendentes.iterrows():
                col_inf, col_btn = st.columns([3, 1])
                col_inf.warning(f"SOLICITAÇÃO: {r['nivel']} | Loja {r['loja_id']} ({r['cidade']})")
                if col_btn.button("✅ ACEITAR", key=r['device_id']):
                    cursor.execute("UPDATE dispositivos_autorizados SET aprovado = 1 WHERE device_id = ?", (r['device_id'],))
                    conn.commit()
                    st.rerun()
        else: st.info("Nenhuma solicitação no momento.")
        conn.close()

# --- DEMAIS TELAS (RESUMIDAS) ---
elif perfil_selecionado == "Aguardando Liberação":
    st.title("⏳ Verificação em Andamento")
    st.info("Este aparelho enviou uma solicitação. Aguarde o Administrador aceitar no painel principal.")

elif perfil_selecionado == "Funcionário":
    st.title(f"🛒 Balcão - Loja {loja_id} ({cidade_user})")
    st.write("Área de vendas pronta para uso.")

elif perfil_selecionado == "Fábrica":
    st.title(f"🏭 Produção - {cidade_user}")
    st.write("Área de envio de estoque pronta.")
