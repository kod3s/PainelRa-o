from supabase import create_client
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Indicadores Ração SDR", layout="wide")

# =========================
# CONEXÃO SUPABASE
# =========================
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["service_key"]
supabase = create_client(url, key)

st.title("Painel de Desvios - Ração Sidrolândia")

st.sidebar.header("Upload das Planilhas")

arquivo_prog = st.sidebar.file_uploader("Programacao.xlsx", type=["xlsx"])
arquivo_prod = st.sidebar.file_uploader("Producao.xlsx", type=["xlsx"])
arquivo_ent = st.sidebar.file_uploader("Entregas.xlsx", type=["xlsx"])


# =========================
# FUNÇÃO SEGURA
# =========================
def preparar_df(df):
    df.columns = df.columns.str.strip()
    df = df.replace({np.nan: None})

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")

    return df


def inserir_sem_upsert(nome_tabela, df):
    if df.empty:
        st.warning(f"{nome_tabela} vazio.")
        return

    registros = df.to_dict(orient="records")

    try:
        supabase.table(nome_tabela).insert(registros).execute()
        st.success(f"{nome_tabela} inserido com sucesso.")
    except Exception as e:
        st.error(f"Erro ao inserir {nome_tabela}: {e}")
        st.json(registros[0])
        st.stop()


# =========================
# UPLOAD
# =========================
if arquivo_prog and arquivo_prod and arquivo_ent:

    # PROGRAMACAO
    df_prog = preparar_df(pd.read_excel(arquivo_prog))

    df_prog = df_prog.rename(columns={
        "Data Pedido": "data_pedido",
        "Quantidade Pedido": "quantidade_pedido"
    })

    df_prog = df_prog.dropna(subset=["data_pedido"])

    inserir_sem_upsert("programacao", df_prog)

    # PRODUCAO
    df_prod = preparar_df(pd.read_excel(arquivo_prod))

    df_prod = df_prod.rename(columns={
        "Data": "data",
        "Inicial": "inicial",
        "Final": "final",
        "Quantidade": "quantidade"
    })

    df_prod = df_prod.dropna(subset=["data"])

    inserir_sem_upsert("producao", df_prod)

    # ENTREGAS
    df_ent = preparar_df(pd.read_excel(arquivo_ent))

    df_ent = df_ent.rename(columns={
        "Data Transação": "data_transacao",
        "Placa Veículo": "placa_veiculo",
        "Cód.Viagem Tpt.": "cod_viagem",
        "Total (Kg)": "total_kg"
    })

    df_ent = df_ent.dropna(subset=["data_transacao"])

    inserir_sem_upsert("entregas", df_ent)

else:
    st.warning("Envie as 3 planilhas.")
    st.stop()


# =========================
# BUSCAR DADOS
# =========================
df_prog = pd.DataFrame(supabase.table("programacao").select("*").execute().data or [])
df_prod = pd.DataFrame(supabase.table("producao").select("*").execute().data or [])
df_ent = pd.DataFrame(supabase.table("entregas").select("*").execute().data or [])

if df_prog.empty or df_prod.empty or df_ent.empty:
    st.warning("Banco ainda sem dados.")
    st.stop()


# =========================
# CONVERSÕES
# =========================
df_prog["quantidade_pedido"] = pd.to_numeric(df_prog["quantidade_pedido"], errors="coerce").fillna(0)
df_prod["quantidade"] = pd.to_numeric(df_prod["quantidade"], errors="coerce").fillna(0)
df_ent["total_kg"] = pd.to_numeric(df_ent["total_kg"], errors="coerce").fillna(0)

prog_total = df_prog["quantidade_pedido"].sum() / 1000
prod_total = df_prod["quantidade"].sum() / 1000
ent_total = df_ent["total_kg"].sum() / 1000

st.subheader("Totais Gerais")

col1, col2, col3 = st.columns(3)
col1.metric("Programado (ton)", f"{prog_total:,.2f}")
col2.metric("Produzido (ton)", f"{prod_total:,.2f}")
col3.metric("Entregue (ton)", f"{ent_total:,.2f}")
