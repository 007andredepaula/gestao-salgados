import streamlit as st
import sqlite3
import pandas as pd
import uuid
import secrets
from datetime import datetime, timedelta
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Gestão Integrada - Fábrica de Salgados", layout="wide")

# --- CONEXÃO COM BANCO DE DADOS ---
def criar_conexao():
    return sqlite3.connect('gestao_integrada.db', check_same_thread=False)

def inicializar_banco():
    conn = criar_conexao()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS regionais (id INTEGER PRIMARY KEY, cidade TEXT, meta_mensal REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS dispositivos_autorizados (device_id TEXT PRIMARY KEY, loja_id INTEGER, aprovado BOOLEAN DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS tokens_acesso (token TEXT PRIMARY KEY, loja_id INTEGER, status TEXT, expiracao TIMESTAMP)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY, loja_id INTEGER, produto TEXT, quantidade INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY, loja_id INTEGER, produto TEXT, valor REAL, quantidade INTEGER, data TIMESTAMP)''')
    
    # Inserir dados iniciais se vazio
    cursor.execute("SELECT count(*) FROM estoque")
    if cursor.fetchone()[0] == 0:
        produtos = [('Cento de Coxinha', 20), ('Cento de Kibe', 20), ('Combo Festa', 15)]
        for p in produtos:
            cursor.execute("INSERT INTO estoque (loja_id, produto, quantidade) VALUES (1, ?, ?)", (p[0], p[1]))
    conn.commit()
    conn.close()

inicializar_banco()

# --- FUNÇÕES DE APOIO ---
def get_device_id():
    return str(uuid.getnode())

def verificar_acesso():
    dev_id = get_device_id()
    conn = criar_conexao()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT aprovado, loja_id FROM dispositivos_autorizados WHERE device_id = ? AND aprovado = 1", (dev_id,))
        resultado = cursor.fetchone()
    except: resultado = None
    conn.close()
    return resultado

def enviar_whatsapp(produto, qtd, loja):
    # Substitua pelo seu número de administrador (Ex: 5527999999999)
    telefone = "5527999999999" 
    mensagem = f"⚠️ *ALERTA DE ESTOQUE BAIXO*\n\nLoja: {loja}\nProduto: {produto}\nQuantidade Atual: {qtd} unidades.\n\n*Necessário reposição urgente!*"
    texto_url = urllib.parse.quote(mensagem)
    link = f"https://wa.me/{telefone}?text={texto_url}"
    return link

# --- LOGICA DE TOKEN ---
query_params = st.query_params
if "token" in query_params:
    token_url = query_params["token"]
    conn = criar_conexao(); cursor = conn.cursor()
    cursor.execute("SELECT loja_id FROM tokens_acesso WHERE token = ? AND status = 'pendente'", (token_url,))
    res = cursor.fetchone()
    if res:
        cursor.execute("INSERT OR REPLACE INTO dispositivos_autorizados VALUES (?, ?, 0)", (get_device_id(), res[0]))
        cursor.execute("UPDATE tokens_acesso SET status = 'utilizado' WHERE token = ?", (token_url,))
        conn.commit()
        st.success("Aparelho registrado! Aguarde aprovação.")
    conn.close()

# --- INTERFACE ---
st.sidebar.title("🥨 Gestão de Fábrica")
perfil = st.sidebar.selectbox("Acesso", ["Funcionário", "Gerente", "Administrador"])
acesso_info = verificar_acesso()
status_acesso = acesso_info is not None
loja_id_atual = acesso_info[1] if status_acesso else None

if perfil in ["Funcionário", "Gerente"] and not status_acesso:
    st.title("🚫 Acesso Restrito")
    st.stop()

# --- TELAS ---
if perfil == "Administrador":
    st.title("🏛️ Painel do Administrador Geral")
    t1, t2, t3 = st.tabs(["Segurança", "Fábrica (Envio)", "Relatórios"])
    
    with t1:
        loja_alvo = st.number_input("ID da Loja", 1, 10, 1)
        if st.button("Gerar Link"):
            tk = secrets.token_urlsafe(16)
            conn = criar_conexao(); cursor = conn.cursor()
            cursor.execute("INSERT INTO tokens_acesso VALUES (?, ?, 'pendente', ?)", (tk, loja_alvo, datetime.now()+timedelta(hours=24)))
            conn.commit(); conn.close()
            st.code(f"https://sistema-gestao.streamlit.app/?token={tk}")
            
    with t2:
        st.subheader("📦 Abastecer Lojas")
        col1, col2, col3 = st.columns(3)
        l_dest = col1.number_input("Loja Destino", 1, 10, 1)
        p_envio = col2.selectbox("Produto", ["Cento de Coxinha", "Cento de Kibe", "Combo Festa"])
        q_envio = col3.number_input("Qtd Enviada", 1, 500, 50)
        if st.button("Confirmar Envio"):
            conn = criar_conexao(); cursor = conn.cursor()
            # Verifica se já existe o produto na loja para dar UPDATE ou INSERT
            cursor.execute("SELECT id FROM estoque WHERE loja_id = ? AND produto = ?", (l_dest, p_envio))
            if cursor.fetchone():
                cursor.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE loja_id = ? AND produto = ?", (q_envio, l_dest, p_envio))
            else:
                cursor.execute("INSERT INTO estoque (loja_id, produto, quantidade) VALUES (?, ?, ?)", (l_dest, p_envio, q_envio))
            conn.commit(); conn.close()
            st.success("Estoque enviado!")

elif perfil == "Funcionário":
    st.title(f"🛒 PDV - Loja {loja_id_atual}")
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Nova Venda")
        v_prod = st.selectbox("Produto", ["Cento de Coxinha", "Cento de Kibe", "Combo Festa"])
        v_qtd = st.number_input("Qtd", 1, 100, 1)
        v_valor = st.number_input("Total R$", 0.0, 5000.0, 50.0)
        
        if st.button("Finalizar Venda"):
            conn = criar_conexao(); cursor = conn.cursor()
            cursor.execute("INSERT INTO vendas (loja_id, produto, valor, quantidade, data) VALUES (?, ?, ?, ?, ?)", 
                           (loja_id_atual, v_prod, v_valor, v_qtd, datetime.now()))
            cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE loja_id = ? AND produto = ?", (v_qtd, loja_id_atual, v_prod))
            conn.commit(); conn.close()
            st.success("Venda Concluída!")
            st.rerun()

    with c2:
        st.subheader("📦 Estoque Local")
        conn = criar_conexao()
        df_est = pd.read_sql_query(f"SELECT produto, quantidade FROM estoque WHERE loja_id = {loja_id_atual}", conn)
        conn.close()
        
        for _, row in df_est.iterrows():
            st.write(f"**{row['produto']}:** {row['quantidade']}")
            if row['quantidade'] < 10:
                st.error(f"⚠️ {row['produto']} CRÍTICO!")
                link_wa = enviar_whatsapp(row['produto'], row['quantidade'], f"Guarapari - Loja {loja_id_atual}")
                st.link_button("📲 Avisar Fábrica (WhatsApp)", link_wa)

elif perfil == "Gerente":
    st.title(f"📊 Dashboard Gerencial - Loja {loja_id_atual}")
    conn = criar_conexao()
    vendas = pd.read_sql_query(f"SELECT * FROM vendas WHERE loja_id = {loja_id_atual}", conn)
    st.metric("Vendas Totais", f"R$ {vendas['valor'].sum():,.2f}")
    st.dataframe(vendas)
    conn.close()
