from supabase import create_client
import streamlit as st
import pandas as pd
import numpy as np
import datetime

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
# CONVERSÃO SEGURA FINAL
# =========================
def limpar_registro(reg):
    novo = {}

    for k, v in reg.items():

        if pd.isna(v):
            novo[k] = None

        elif isinstance(v, (pd.Timestamp, datetime.datetime, datetime.date)):
            novo[k] = v.strftime("%Y-%m-%d")

        elif isinstance(v, (np.integer,)):
            novo[k] = int(v)

        elif isinstance(v, (np.floating,)):
            novo[k] = float(v)

        else:
            novo[k] = v

    return novo


def enviar(nome_tabela, df):
    if df.empty:
        st.warning(f"{nome_tabela} vazio.")
        return

    registros = df.to_dict(orient="records")
    registros_limpos = [limpar_registro(r) for r in registros]

    try:
        supabase.table(nome_tabela).insert(registros_limpos).execute()
        st.success(f"{nome_tabela} inserido com sucesso.")
    except Exception as e:
        st.error(f"Erro ao inserir {nome_tabela}: {e}")
        st.json(registros_limpos[0])
        st.stop()


# =========================
# UPLOAD
# =========================
if arquivo_prog and arquivo_prod and arquivo_ent:

    # PROGRAMACAO
df_prog = pd.read_excel(arquivo_prog)
df_prog.columns = df_prog.columns.str.strip()

df_prog = df_prog.rename(columns={
    "Tipo Fazenda": "tipo_fazenda",
    "Data Pedido": "data_pedido",
    "Data Carga": "data_carga",
    "Idade": "idade",
    "Código Ração": "codigo_racao",
    "Nome Fazenda": "nome_fazenda",
    "Quantidade Pedido": "quantidade_pedido",
    "Observações": "observacoes",
    "Nome Ração": "nome_racao",
    "KM": "km",
    "Motorista": "motorista",
    "Município": "municipio",
    "Localidade": "localidade",
    "Fábrica Rações": "fabrica_racoes",
    "Nome Motorista": "nome_motorista"
})

# ⚠️ DEBUG IMPORTANTE
st.write("Colunas após rename:")
st.write(df_prog.columns.tolist())

enviar("programacao", df_prog)

    # PRODUCAO
    df_prod = pd.read_excel(arquivo_prod)
    df_prod.columns = df_prod.columns.str.strip()

    df_prod = df_prod.rename(columns={
        "Data": "data",
        "Inicial": "inicial",
        "Final": "final",
        "Quantidade": "quantidade"
    })

    df_prod = df_prod.dropna(subset=["data"])

    enviar("producao", df_prod)

    # ENTREGAS
    df_ent = pd.read_excel(arquivo_ent)
    df_ent.columns = df_ent.columns.str.strip()

    df_ent = df_ent.rename(columns={
        "Data Transação": "data_transacao",
        "Placa Veículo": "placa_veiculo",
        "Cód.Viagem Tpt.": "cod_viagem",
        "Total (Kg)": "total_kg"
    })

    df_ent = df_ent.dropna(subset=["data_transacao"])

    enviar("entregas", df_ent)

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
# TOTAIS
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

