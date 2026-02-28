import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(page_title="Indicadores Ração SDR", layout="wide")
st.title("Painel de desvios - Ração Sidrolândia")

# Conexão com o banco (usar secrets do Streamlit)
engine = create_engine(st.secrets["DATABASE_URL"])

# =========================================================
# UPLOAD DE PLANILHAS
# =========================================================

st.sidebar.header("Upload das Planilhas")

arquivo_prog = st.sidebar.file_uploader("Programacao.xlsx", type=["xlsx"])
arquivo_prod = st.sidebar.file_uploader("Producao.xlsx", type=["xlsx"])
arquivo_ent = st.sidebar.file_uploader("Entregas.xlsx", type=["xlsx"])

# =========================================================
# SALVAR NO BANCO (SÓ SE CLICAR)
# =========================================================

if arquivo_prog and arquivo_prod and arquivo_ent:

    df_prog_upload = pd.read_excel(arquivo_prog)
    df_prod_upload = pd.read_excel(arquivo_prod)
    df_ent_upload = pd.read_excel(arquivo_ent)

    if st.sidebar.button("Salvar no Banco"):

        with engine.begin() as conn:  # transação automática

            # PROGRAMACAO
            df_prog_db = df_prog_upload[["Data Pedido", "Quantidade Pedido"]].copy()
            df_prog_db.columns = ["data_pedido", "quantidade_pedido"]

            conn.execute(text("DELETE FROM programacao"))
            df_prog_db.to_sql("programacao", conn, if_exists="append", index=False)

            # PRODUCAO
            df_prod_db = df_prod_upload[["Data", "Inicial", "Final", "Quantidade"]].copy()
            df_prod_db.columns = ["data", "inicial", "final", "quantidade"]

            conn.execute(text("DELETE FROM producao"))
            df_prod_db.to_sql("producao", conn, if_exists="append", index=False)

            # ENTREGAS
            df_ent_db = df_ent_upload[[
                "Data Transação",
                "Placa Veículo",
                "Cód.Viagem Tpt.",
                "Total (Kg)"
            ]].copy()
            df_ent_db.columns = [
                "data_transacao",
                "placa_veiculo",
                "cod_viagem",
                "total_kg"
            ]

            conn.execute(text("DELETE FROM entregas"))
            df_ent_db.to_sql("entregas", conn, if_exists="append", index=False)

        st.sidebar.success("Dados salvos no banco!")

# =========================================================
# LER DO BANCO (SEMPRE)
# =========================================================

df_prog = pd.read_sql("SELECT * FROM programacao", engine)
df_prod = pd.read_sql("SELECT * FROM producao", engine)
df_ent = pd.read_sql("SELECT * FROM entregas", engine)

# Aviso se banco estiver vazio
if df_prog.empty or df_prod.empty or df_ent.empty:
    st.warning("Banco vazio. Faça upload e clique em 'Salvar no Banco'.")
    st.stop()

# =========================================================
# AJUSTE DE NOMES PARA SUA LÓGICA
# =========================================================

df_prog.columns = ["id", "Data Pedido", "Quantidade Pedido"]
df_prod.columns = ["id", "Data", "Inicial", "Final", "Quantidade"]
df_ent.columns = ["id", "Data Transação", "Placa Veículo", "Cód.Viagem Tpt.", "Total (Kg)"]

# =========================================================
# CONVERSÃO DE DATAS
# =========================================================

df_prog["Data Pedido"] = pd.to_datetime(df_prog["Data Pedido"])
df_prod["Data"] = pd.to_datetime(df_prod["Data"])
df_ent["Data Transação"] = pd.to_datetime(df_ent["Data Transação"])

# =========================================================
# FILTRO DE PERÍODO
# =========================================================

st.subheader("Filtro de Período")

data_inicio, data_fim = st.date_input(
    "Selecione o período",
    [df_ent["Data Transação"].min(), df_ent["Data Transação"].max()]
)

df_prog = df_prog[
    (df_prog["Data Pedido"] >= pd.to_datetime(data_inicio)) &
    (df_prog["Data Pedido"] <= pd.to_datetime(data_fim))
]

df_prod = df_prod[
    (df_prod["Data"] >= pd.to_datetime(data_inicio)) &
    (df_prod["Data"] <= pd.to_datetime(data_fim))
]

df_ent = df_ent[
    (df_ent["Data Transação"] >= pd.to_datetime(data_inicio)) &
    (df_ent["Data Transação"] <= pd.to_datetime(data_fim))
]

# =========================================================
# RESTO DO SEU CÓDIGO (Indicadores, Gráficos, etc.)
# =========================================================

# Aqui você continua com suas métricas, dashboards, gráficos e cards
# por exemplo:
# total_programado = df_prog["Quantidade Pedido"].sum()
# total_entregue = df_ent["Total (Kg)"].sum()
# st.metric("Total Programado", total_programado)
# st.metric("Total Entregue", total_entregue)
