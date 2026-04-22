import streamlit as st
import sqlite3
import pandas as pd
import uuid
import secrets
from datetime import datetime, timedelta
import urllib.parse

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
    # Busca o status exato do aparelho atual
    cursor.execute("SELECT aprovado, loja_id, nivel, cidade FROM dispositivos_autorizados WHERE device_id = ?", (get_device_id(),))
    res = cursor.fetchone(); conn.close()
    return res 

# --- CAPTURA DE TOKEN ---
qp = st.query_params
if "token" in qp:
    token_val = qp["token"]
    conn = criar_conexao(); cursor = conn.cursor()
    cursor.execute("SELECT loja_id, nivel, cidade FROM tokens_acesso WHERE token = ? AND status = 'pendente'", (token_val,))
    res = cursor.fetchone()
    if res:
        cursor.execute("INSERT OR REPLACE INTO dispositivos_autorizados VALUES (?, ?, ?, ?, 0)", (get_device_id(), res[0], res[1], res[2]))
        cursor.execute("UPDATE tokens_acesso SET status = 'utilizado' WHERE token = ?", (token_val,))
        conn.commit()
        st.success("✅ Solicitação enviada! Aguarde a aprovação do Administrador.")
        st.info("Após o Admin aprovar, esta página irá carregar automaticamente.")
    conn.close()

# --- LOGICA DE NAVEGAÇÃO ---
acesso = verificar_acesso()
st.sidebar.title("🥨 Gestão de Fábrica")

# Se o aparelho não existe ou não está aprovado
if not acesso or acesso[0] == 0:
    perfil_selecionado = st.sidebar.selectbox("Acesso", ["Aguardando Liberação", "Login Administrador"])
    if acesso and acesso[0] == 0:
        st.sidebar.warning("⏳ Aguardando Aprovação...")
else:
    status, loja_id_atual, nivel_user, cidade_user = acesso
    st.sidebar.success(f"Dispositivo Autorizado")
    st.sidebar.info(f"📍 {cidade_user} | {nivel_user}")
    
    # Trava de segurança: Funcionário não vê opção de Admin
    if nivel_user == "Funcionário":
        perfil_selecionado = "Funcionário"
    elif nivel_user == "Gerente":
        perfil_selecionado = st.sidebar.selectbox("Menu", ["Gerente", "Funcionário"])
    else: # Admin
        perfil_selecionado = st.sidebar.selectbox("Menu", ["Administrador", "Fábrica", "Gerente", "Funcionário"])

# --- TELAS ---

if perfil_selecionado == "Aguardando Liberação":
    st.title("⏳ Verificação de Segurança")
    st.write("Este dispositivo está aguardando liberação do Administrador Geral.")
    if st.button("🔄 Verificar se fui aprovado"):
        st.rerun()

elif perfil_selecionado == "Login Administrador" or perfil_selecionado == "Administrador":
    if 'auth' not in st.session_state: st.session_state['auth'] = False
    if not st.session_state['auth']:
        u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u == ADMIN_USER and p == ADMIN_PASS:
                st.session_state['auth'] = True; st.rerun()
        st.stop()

    st.title("🏛️ Painel do Administrador")
    t1, t2 = st.tabs(["Aprovações e Links", "Relatórios"])
    
    with t1:
        st.subheader("Novas Solicitações")
        conn = criar_conexao(); cursor = conn.cursor()
        pendentes = pd.read_sql_query("SELECT * FROM dispositivos_autorizados WHERE aprovado = 0", conn)
        for _, r in pendentes.iterrows():
            if st.button(f"✅ Autorizar: {r['nivel']} - Loja {r['loja_id']} ({r['cidade']})"):
                cursor.execute("UPDATE dispositivos_autorizados SET aprovado = 1 WHERE device_id = ?", (r['device_id'],))
                conn.commit(); conn.close(); st.rerun()
        conn.close()
        
        st.divider()
        st.subheader("Gerar Convite")
        # (Campos de gerar link...)
        l_id = st.number_input("ID Loja", 1, 10, 1)
        cid = st.selectbox("Cidade", ["Guarapari", "Vitoria"])
        niv = st.selectbox("Nível", ["Funcionário", "Gerente", "Fábrica"])
        if st.button("Gerar Link"):
            tk = secrets.token_urlsafe(16)
            conn = criar_conexao(); cursor = conn.cursor()
            cursor.execute("INSERT INTO tokens_acesso VALUES (?, ?, ?, ?, 'pendente', ?)", (tk, l_id, niv, cid, datetime.now()+timedelta(hours=24)))
            conn.commit(); conn.close()
            st.code(f"https://sistema-gestao.streamlit.app/?token={tk}")

elif perfil_selecionado == "Funcionário":
    st.title(f"🛒 Balcão de Vendas - Loja {loja_id_atual}")
    st.subheader(f"Unidade: {cidade_user}")
    
    # FORMULÁRIO DE VENDA REAL
    with st.form("venda_form"):
        prod = st.selectbox("Produto", ["Cento de Coxinha", "Cento de Kibe", "Combo Festa"])
        qtd = st.number_input("Quantidade", 1, 100, 1)
        valor = st.number_input("Valor Total R$", 0.0, 1000.0, 60.0)
        if st.form_submit_button("Finalizar Venda"):
            conn = criar_conexao(); cursor = conn.cursor()
            cursor.execute("INSERT INTO vendas (loja_id, cidade, produto, valor, quantidade, data) VALUES (?, ?, ?, ?, ?, ?)",
                           (loja_id_atual, cidade_user, prod, valor, qtd, datetime.now()))
            conn.commit(); conn.close()
            st.success("Venda salva com sucesso!")

elif perfil_selecionado == "Fábrica":
    st.title(f"🏭 Produção Regional - {cidade_user}")
    st.write("Painel para envio de mercadorias.")
