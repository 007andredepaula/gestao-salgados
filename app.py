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

# --- LÓGICA DE PERMISSÕES ---
acesso_db = None
conn = criar_conexao(); cursor = conn.cursor()
cursor.execute("SELECT aprovado, loja_id, nivel, cidade FROM dispositivos_autorizados WHERE device_id = ?", (get_device_id(),))
acesso_db = cursor.fetchone()
conn.close()

# Inicializa sessão de autenticação
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

# --- BARRA LATERAL ---
st.sidebar.title("🥨 Gestão de Fábrica")

# Se você já logou como Admin, ou se o dispositivo é Admin
if st.session_state['is_admin']:
    perfil_selecionado = st.sidebar.selectbox("Painel Geral", ["Administrador", "Fábrica", "Gerente", "Funcionário"])
    
    # ORGANIZAÇÃO DE GUARAPARI NA LATERAL PARA O ADMIN
    with st.sidebar.expander("🌍 Estrutura Guarapari", expanded=True):
        st.subheader("📍 Unidade Guarapari")
        st.write("🏭 **Fábrica Principal**")
        st.write("📂 **Gerências:** Loja 01, Loja 02")
        st.write("🛒 **Caixas:** Balcão 01, Balcão 02")
        
elif acesso_db and acesso_db[0] == 1:
    # DISPOSITIVO DE LOJA: Bloqueado, não pode mudar perfil
    status, loja_id_atual, nivel_user, cidade_user = acesso_db
    st.sidebar.success("✅ Dispositivo Autorizado")
    st.sidebar.info(f"📍 {cidade_user} | {nivel_user}")
    perfil_selecionado = nivel_user # Trava o perfil conforme o banco
else:
    perfil_selecionado = st.sidebar.selectbox("Acesso", ["Login Administrador", "Aguardando Liberação"])

# --- TELAS ---

if perfil_selecionado == "Administrador" or perfil_selecionado == "Login Administrador":
    if not st.session_state['is_admin']:
        st.title("🔐 Acesso Administrativo")
        u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
        if st.button("Entrar no Painel"):
            if u == ADMIN_USER and p == ADMIN_PASS:
                st.session_state['is_admin'] = True
                st.rerun()
            else: st.error("Acesso Negado")
        st.stop()

    st.title("🏛️ Painel do Administrador Geral")
    t1, t2, t3 = st.tabs(["Segurança e Aprovações", "Gestão de Guarapari", "Financeiro"])
    
    with t1:
        st.subheader("Gerar Link para Novo Computador")
        col = st.columns(3)
        l_id = col[0].number_input("ID Loja", 1, 10, 1)
        cid = col[1].selectbox("Cidade", ["Guarapari", "Vitória"])
        niv = col[2].selectbox("Nível do Link", ["Funcionário", "Gerente", "Fábrica"])
        if st.button("Gerar Novo Link"):
            tk = secrets.token_urlsafe(16)
            c = criar_conexao(); cur = c.cursor()
            cur.execute("INSERT INTO tokens_acesso VALUES (?, ?, ?, ?, 'pendente', ?)", (tk, l_id, niv, cid, datetime.now()+timedelta(hours=24)))
            c.commit(); c.close()
            st.code(f"https://sistema-gestao.streamlit.app/?token={tk}")

        st.divider()
        st.subheader("Aprovações Pendentes")
        c = criar_conexao(); cur = c.cursor()
        pendentes = pd.read_sql_query("SELECT * FROM dispositivos_autorizados WHERE aprovado = 0", c)
        for _, r in pendentes.iterrows():
            if st.button(f"✅ Autorizar {r['nivel']} (Loja {r['loja_id']})"):
                cur.execute("UPDATE dispositivos_autorizados SET aprovado = 1 WHERE device_id = ?", (r['device_id'],))
                c.commit(); c.close(); st.rerun()
        c.close()

elif perfil_selecionado == "Funcionário":
    st.title(f"🛒 Balcão - Loja {acesso_db[1]}")
    st.write(f"Unidade: {acesso_db[3]}")
    # Tela simples de venda para o caixa
    with st.form("venda"):
        st.selectbox("Salgado", ["Cento de Coxinha", "Cento de Kibe"])
        st.number_input("Qtd", 1)
        if st.form_submit_button("Lançar Venda"):
            st.success("Venda registrada!")

elif perfil_selecionado == "Aguardando Liberação":
    st.title("⏳ Verificação de Dispositivo")
    st.warning("Peça ao Administrador para aprovar este computador no painel principal.")
    if st.button("🔄 Já fui aprovado"): st.rerun()
