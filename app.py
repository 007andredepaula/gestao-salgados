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
    return sqlite3.connect('gestao_integrada.db', check_same_thread=False)

def inicializar_banco():
    conn = criar_conexao()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS regionais (
        id INTEGER PRIMARY KEY, cidade TEXT, meta_mensal REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS dispositivos_autorizados (
        device_id TEXT PRIMARY KEY, loja_id INTEGER, aprovado BOOLEAN DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tokens_acesso (
        token TEXT PRIMARY KEY, loja_id INTEGER, status TEXT, expiracao TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY, loja_id INTEGER, valor REAL, data TIMESTAMP, cidade TEXT)''')
    conn.commit()
    conn.close()

inicializar_banco()

# --- LÓGICA DE IDENTIFICAÇÃO ---
def get_device_id():
    return str(uuid.getnode())

def verificar_acesso():
    dev_id = get_device_id()
    conn = criar_conexao()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT aprovado FROM dispositivos_autorizados WHERE device_id = ? AND aprovado = 1", (dev_id,))
        autorizado = cursor.fetchone()
    except:
        autorizado = None
    conn.close()
    return autorizado is not None

# --- LÓGICA DE CAPTURA DE TOKEN ---
query_params = st.query_params
if "token" in query_params:
    token_url = query_params["token"]
    conn = criar_conexao()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT loja_id FROM tokens_acesso WHERE token = ? AND status = 'pendente'", (token_url,))
        resultado = cursor.fetchone()
        if resultado:
            loja_id_token = resultado[0]
            dev_id_atual = get_device_id()
            cursor.execute("INSERT OR REPLACE INTO dispositivos_autorizados (device_id, loja_id, aprovado) VALUES (?, ?, 0)", (dev_id_atual, loja_id_token))
            cursor.execute("UPDATE tokens_acesso SET status = 'utilizado' WHERE token = ?", (token_url,))
            conn.commit()
            st.success("✅ Aparelho registrado! Peça aprovação ao Administrador.")
    except Exception as e:
        st.error(f"Erro ao processar token: {e}")
    conn.close()

# --- INTERFACE ---
st.sidebar.title("🥨 Gestão de Fábrica")
perfil = st.sidebar.selectbox("Acesso", ["Funcionário", "Gerente", "Administrador"])
status_acesso = verificar_acesso()

if perfil in ["Funcionário", "Gerente"] and not status_acesso:
    st.title("🚫 Acesso Restrito")
    st.warning("Dispositivo não autorizado.")
    st.stop()

if perfil == "Administrador":
    st.title("🏛️ Painel do Administrador Geral")
    tab1, tab2, tab3 = st.tabs(["Segurança e Dispositivos", "Metas Regionais", "Financeiro"])
    
    with tab1:
        st.subheader("Gerar Link de Acesso Único")
        loja_alvo = st.number_input("ID da Loja Destino", min_value=1, max_value=10, step=1)
        
        if st.button("Gerar Novo Link"):
            inicializar_banco() 
            novo_token = secrets.token_urlsafe(16)
            conn = criar_conexao()
            cursor = conn.cursor()
            expira = datetime.now() + timedelta(hours=24)
            
            try:
                # CORREÇÃO AQUI: 4 campos na tabela (token, loja_id, status, expiracao) e 4 valores (?, ?, ?, ?)
                cursor.execute(
                    "INSERT INTO tokens_acesso (token, loja_id, status, expiracao) VALUES (?, ?, ?, ?)", 
                    (novo_token, int(loja_alvo), 'pendente', expira)
                )
                conn.commit()
                url_real = "https://sistema-gestao.streamlit.app"
                st.success(f"Link gerado para Loja {loja_alvo}:")
                st.code(f"{url_real}/?token={novo_token}")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
            finally:
                conn.close()

        st.divider()
        st.subheader("Aprovações Pendentes")
        try:
            conn = criar_conexao()
            df_pendentes = pd.read_sql_query("SELECT device_id, loja_id FROM dispositivos_autorizados WHERE aprovado = 0", conn)
            if not df_pendentes.empty:
                for _, row in df_pendentes.iterrows():
                    col1, col2 = st.columns([3, 1])
                    col1.warning(f"Aparelho {row['device_id']} (Loja {row['loja_id']})")
                    if col2.button("Aprovar", key=row['device_id']):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE dispositivos_autorizados SET aprovado = 1 WHERE device_id = ?", (row['device_id'],))
                        conn.commit()
                        st.success("Aprovado com sucesso!")
                        st.rerun()
            else:
                st.info("Nenhuma solicitação pendente.")
            conn.close()
        except:
            st.info("Aguardando primeiras conexões...")

elif perfil == "Gerente":
    st.title("📊 Painel de Gerenciamento")
    st.info("Área de metas e bônus em desenvolvimento.")
elif perfil == "Funcionário":
    st.title("🛒 Operação de Loja")
    st.write("Registro de vendas em desenvolvimento.")