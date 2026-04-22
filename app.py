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

# --- VERIFICAÇÃO DE DISPOSITIVO NO BANCO ---
conn = criar_conexao(); cursor = conn.cursor()
cursor.execute("SELECT aprovado, loja_id, nivel, cidade FROM dispositivos_autorizados WHERE device_id = ?", (get_device_id(),))
acesso_db = cursor.fetchone()
conn.close()

# Controle de Sessão de Admin
if 'sessao_admin' not in st.session_state:
    st.session_state['sessao_admin'] = False

# --- BARRA LATERAL (MENU DE ACESSO) ---
st.sidebar.title("🥨 Gestão de Fábrica")

opcoes_menu = []

# Se você já logou como Admin, libera tudo
if st.session_state['sessao_admin']:
    opcoes_menu = ["Administrador", "Fábrica", "Gerente", "Funcionário"]
    perfil_selecionado = st.sidebar.selectbox("Navegação Geral", opcoes_menu)
    
    # ESTRUTURA HIERÁRQUICA DE GUARAPARI (Visual para o Admin)
    with st.sidebar.expander("📍 Unidade: Guarapari", expanded=True):
        st.markdown("---")
        st.write("🏭 **Fábrica Principal**")
        st.write("👤 **Gerentes:** Loja 01, Loja 02")
        st.write("🛒 **Balcões:** Caixa 01, Caixa 02")
        st.markdown("---")

# Se o dispositivo está autorizado no banco (como o seu está)
elif acesso_db and acesso_db[0] == 1:
    status, loja_id_atual, nivel_user, cidade_user = acesso_db
    st.sidebar.success("✅ Dispositivo de Loja Autorizado")
    # Aqui está o segredo: mesmo sendo balcão, permitimos que VOCÊ mude para Login Admin
    perfil_selecionado = st.sidebar.selectbox("Função", [nivel_user, "Login Administrador"])

# Se for um dispositivo novo ou deslogado
else:
    perfil_selecionado = st.sidebar.selectbox("Acesso", ["Login Administrador", "Aguardando Liberação"])

# --- TELAS ---

# 1. TELA DE LOGIN / PAINEL ADMIN
if perfil_selecionado == "Login Administrador" or perfil_selecionado == "Administrador":
    if not st.session_state['sessao_admin']:
        st.title("🏛️ Acesso ao Painel do Administrador")
        col1, col2 = st.columns(2)
        u = col1.text_input("Usuário Admin")
        p = col2.text_input("Senha Mestra", type="password")
        if st.button("🔓 Entrar como Administrador"):
            if u == ADMIN_USER and p == ADMIN_PASS:
                st.session_state['sessao_admin'] = True
                st.rerun()
            else: st.error("Credenciais Inválidas")
        st.stop()

    # --- PAINEL DO ADMINISTRADOR REAL ---
    st.title("🏛️ Painel de Controle Geral")
    t1, t2 = st.tabs(["Aprovações e Dispositivos", "Relatórios Financeiros"])
    
    with t1:
        st.subheader("Gerar Acesso para Novas Lojas/Fábricas")
        c1, c2, c3 = st.columns(3)
        l_id = c1.number_input("ID da Loja", 1, 20, 1)
        cid = c2.selectbox("Cidade Atuação", ["Guarapari", "Vitória"])
        niv = c3.selectbox("Tipo de Acesso", ["Funcionário", "Gerente", "Fábrica"])
        if st.button("Gerar Link de Convite"):
            tk = secrets.token_urlsafe(16)
            c = criar_conexao(); cur = c.cursor()
            cur.execute("INSERT INTO tokens_acesso VALUES (?, ?, ?, ?, 'pendente', ?)", (tk, l_id, niv, cid, datetime.now()+timedelta(hours=24)))
            c.commit(); c.close()
            st.code(f"https://fabrica-salgados.streamlit.app/?token={tk}")

        st.divider()
        st.subheader("Solicitações Pendentes (Aprovar Dispositivos)")
        c = criar_conexao(); cur = c.cursor()
        pendentes = pd.read_sql_query("SELECT * FROM dispositivos_autorizados WHERE aprovado = 0", c)
        if not pendentes.empty:
            for _, r in pendentes.iterrows():
                if st.button(f"✅ Autorizar {r['nivel']} - Loja {r['loja_id']} ({r['cidade']})", key=r['device_id']):
                    cur.execute("UPDATE dispositivos_autorizados SET aprovado = 1 WHERE device_id = ?", (r['device_id'],))
                    c.commit(); c.close(); st.rerun()
        else: st.info("Nenhuma solicitação nova.")
        c.close()

# 2. TELA DE BALCÃO (FUNCIONÁRIO)
elif perfil_selecionado == "Funcionário":
    st.title(f"🛒 Balcão de Vendas - Loja {acesso_db[1]}")
    st.info(f"Unidade: {acesso_db[3]} | Função: {acesso_db[2]}")
    # Aqui o funcionário não tem acesso a botões de admin, fica preso no PDV
    with st.form("pdv_venda"):
        st.selectbox("Produto", ["Cento de Coxinha", "Cento de Kibe"])
        st.number_input("Quantidade", 1)
        if st.form_submit_button("Lançar Venda"):
            st.success("Venda enviada ao sistema!")

elif perfil_selecionado == "Aguardando Liberação":
    st.title("⏳ Verificação em Andamento")
    st.warning("Este computador enviou um pedido de acesso. Peça ao Admin para autorizar.")
    if st.button("🔄 Atualizar Status"): st.rerun()
