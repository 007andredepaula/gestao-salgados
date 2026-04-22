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
    # Usamos check_same_thread=False para evitar erros de concorrência no servidor
    conn = sqlite3.connect('gestao_integrada.db', check_same_thread=False)
    return conn

def inicializar_banco():
    conn = criar_conexao()
    cursor = conn.cursor()
    
    # Tabela de Unidades Regionais
    cursor.execute('''CREATE TABLE IF NOT EXISTS regionais (
        id INTEGER PRIMARY KEY, cidade TEXT, meta_mensal REAL)''')
    
    # Tabela de Dispositivos Autorizados
    cursor.execute('''CREATE TABLE IF NOT EXISTS dispositivos_autorizados (
        device_id TEXT PRIMARY KEY, loja_id INTEGER, aprovado BOOLEAN DEFAULT 0)''')
    
    # Tabela de Tokens de Uso Único
    cursor.execute('''CREATE TABLE IF NOT EXISTS tokens_acesso (
        token TEXT PRIMARY KEY, loja_id INTEGER, status TEXT, expiracao TIMESTAMP)''')
    
    # Tabela de Vendas
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY, loja_id INTEGER, valor REAL, data TIMESTAMP, cidade TEXT)''')

    # Dados Iniciais (Guarapari como padrão)
    cursor.execute("SELECT count(*) FROM regionais")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO regionais (cidade, meta_mensal) VALUES ('Guarapari', 100000.0)")
    
    conn.commit()
    conn.close()

# Inicializa as tabelas ao abrir o app
inicializar_banco()

# --- LÓGICA DE IDENTIFICAÇÃO DO APARELHO ---
def get_device_id():
    # Tenta capturar um ID único do hardware
    return str(uuid.getnode())

def verificar_acesso():
    dev_id = get_device_id()
    conn = criar_conexao()
    cursor = conn.cursor()
    cursor.execute("SELECT aprovado FROM dispositivos_autorizados WHERE device_id = ? AND aprovado = 1", (dev_id,))
    autorizado = cursor.fetchone()
    conn.close()
    return autorizado is not None

# --- LÓGICA DE CAPTURA DE TOKEN (PARA NOVOS APARELHOS) ---
query_params = st.query_params
if "token" in query_params:
    token_url = query_params["token"]
    conn = criar_conexao()
    cursor = conn.cursor()
    
    # Verifica se o token existe e está pendente
    cursor.execute("SELECT loja_id FROM tokens_acesso WHERE token = ? AND status = 'pendente'", (token_url,))
    resultado = cursor.fetchone()
    
    if resultado:
        loja_id_token = resultado[0]
        dev_id_atual = get_device_id()
        
        # Registra o aparelho como pendente (aprovado = 0)
        cursor.execute("INSERT OR REPLACE INTO dispositivos_autorizados (device_id, loja_id, aprovado) VALUES (?, ?, 0)", 
                       (dev_id_atual, loja_id_token))
        
        # Marca o token como utilizado para ninguém mais usar
        cursor.execute("UPDATE tokens_acesso SET status = 'utilizado' WHERE token = ?", (token_url,))
        conn.commit()
        st.success("✅ Este aparelho foi registrado! Peça ao Administrador para aprová-lo no painel.")
    else:
        st.error("❌ Link expirado, inválido ou já utilizado.")
    conn.close()

# --- INTERFACE PRINCIPAL ---

st.sidebar.title("🥨 Gestão de Fábrica")
perfil = st.sidebar.selectbox("Acesso", ["Funcionário", "Gerente", "Administrador"])

# Barra de status do dispositivo no menu lateral
status_acesso = verificar_acesso()
st.sidebar.divider()
st.sidebar.write(f"**Dispositivo:** {'🟢 Autorizado' if status_acesso else '🔴 Bloqueado'}")
st.sidebar.caption(f"ID: {get_device_id()}")

# --- BLOQUEIO DE SEGURANÇA ---
if perfil in ["Funcionário", "Gerente"] and not status_acesso:
    st.title("🚫 Acesso Restrito")
    st.warning("Este dispositivo não tem permissão para operar o sistema. Utilize o link de acesso único enviado pelo administrador.")
    st.stop()

# --- CONTEÚDO POR PERFIL ---

if perfil == "Administrador":
    st.title("🏛️ Painel do Administrador Geral")
    
    tab1, tab2, tab3 = st.tabs(["Segurança e Dispositivos", "Metas Regionais", "Financeiro"])
    
    with tab1:
        st.subheader("Gerar Link de Acesso Único")
        loja_alvo = st.number_input("ID da Loja Destino", min_value=1, max_value=10, step=1)
        
        if st.button("Gerar Novo Link"):
            novo_token = secrets.token_urlsafe(16)
            conn = criar_conexao()
            cursor = conn.cursor()
            expira = datetime.now() + timedelta(hours=24)
            cursor.execute("INSERT INTO tokens_acesso (token, loja_id, status, expiracao) VALUES (?, ?, 'pendente', ?)", 
                           (novo_token, loja_alvo, 'pendente', expira))
            conn.commit()
            conn.close()
            
            # URL real do seu sistema
            link_final = f"https://sistema-gestao.streamlit.app/?token={novo_token}"
            st.success("Link gerado para a Loja " + str(loja_alvo))
            st.code(link_final)

        st.divider()
        st.subheader("Aprovações Pendentes")
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
                    st.rerun()
        else:
            st.info("Não há novos dispositivos aguardando aprovação.")
        conn.close()

elif perfil == "Gerente":
    st.title("📊 Painel de Gerenciamento")
    st.subheader("Bônus e Metas Regionais")
    
    # Simulação de faturamento
    faturamento_guarapari = 85000.0
    meta_guarapari = 100000.0
    
    st.metric("Faturamento Guarapari", f"R$ {faturamento_guarapari:,.2f}", f"{faturamento_guarapari - meta_guarapari:,.2f}")
    st.progress(faturamento_guarapari / meta_guarapari)
    
    if faturamento_guarapari >= meta_guarapari:
        st.success("✅ META ATINGIDA! Bônus regional liberado.")
    else:
        st.error(f"Faltam R$ {meta_guarapari - faturamento_guarapari:,.2f} para liberar o bônus.")

elif perfil == "Funcionário":
    st.title("🛒 Operação de Loja")
    st.write("Venda rápida e baixa de estoque.")
    valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0)
    if st.button("Registrar Venda"):
        st.balloons()
        st.success("Venda registrada com sucesso!")
