import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import streamlit as st

engine = create_engine(st.secrets["DATABASE_URL"])

st.set_page_config(page_title="Indicadores Ração SDR", layout="wide")
st.title("Painel de desvios - Ração Sidrolândia")

# =========================================================
# UPLOAD DAS 3 PLANILHAS (continua na sidebar)
# =========================================================

st.sidebar.header("Upload das Planilhas")

arquivo_prog = st.sidebar.file_uploader("Programacao.xlsx", type=["xlsx"])
arquivo_prod = st.sidebar.file_uploader("Producao.xlsx", type=["xlsx"])
arquivo_ent = st.sidebar.file_uploader("Entregas.xlsx", type=["xlsx"])

df_prog_db = df_prog[["Data Pedido", "Quantidade Pedido"]].copy()
df_prog_db.columns = ["data_pedido", "quantidade_pedido"]

engine.execute("delete from programacao")
df_prog_db.to_sql("programacao", engine, if_exists="append", index=False)

df_prod_db = df_prod[["Data", "Inicial", "Final", "Quantidade"]].copy()
df_prod_db.columns = ["data", "inicial", "final", "quantidade"]

engine.execute("delete from producao")
df_prod_db.to_sql("producao", engine, if_exists="append", index=False)

df_ent_db = df_ent[[
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

engine.execute("delete from entregas")
df_ent_db.to_sql("entregas", engine, if_exists="append", index=False)

df_prog = pd.read_sql("select * from programacao", engine)
df_prod = pd.read_sql("select * from producao", engine)
df_ent = pd.read_sql("select * from entregas", engine)



if not arquivo_prog or not arquivo_prod or not arquivo_ent:
    st.warning("Envie as 3 planilhas.")
    st.stop()

df_prog = pd.read_excel(arquivo_prog)
df_prod = pd.read_excel(arquivo_prod)
df_ent = pd.read_excel(arquivo_ent)

df_prog.columns = df_prog.columns.str.strip()
df_prod.columns = df_prod.columns.str.strip()
df_ent.columns = df_ent.columns.str.strip()

# =========================================================
# DATAS
# =========================================================

df_prog["Data Pedido"] = pd.to_datetime(df_prog["Data Pedido"], errors="coerce")
df_prod["Data"] = pd.to_datetime(df_prod["Data"], errors="coerce")
df_ent["Data Transação"] = pd.to_datetime(df_ent["Data Transação"], errors="coerce")

# =========================================================
# 🔹 FILTRO AGORA NO TOPO DA PÁGINA
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
# NUMÉRICOS
# =========================================================

df_prog["Quantidade Pedido"] = pd.to_numeric(
    df_prog["Quantidade Pedido"], errors="coerce"
).fillna(0)

df_prod["Quantidade"] = pd.to_numeric(
    df_prod["Quantidade"], errors="coerce"
).fillna(0)

df_ent["Total (Kg)"] = pd.to_numeric(
    df_ent["Total (Kg)"], errors="coerce"
).fillna(0)

prog_total = df_prog["Quantidade Pedido"].sum() / 1000
prod_total = df_prod["Quantidade"].sum() / 1000
ent_total = df_ent["Total (Kg)"].sum() / 1000

# =========================================================
# PRODUÇÃO
# =========================================================

df_prod["Inicial_dt"] = pd.to_datetime(
    df_prod["Data"].astype(str) + " " + df_prod["Inicial"].astype(str),
    errors="coerce"
)

df_prod["Final_dt"] = pd.to_datetime(
    df_prod["Data"].astype(str) + " " + df_prod["Final"].astype(str),
    errors="coerce"
)

df_prod["Horas"] = (
    (df_prod["Final_dt"] - df_prod["Inicial_dt"]).dt.total_seconds() / 3600
)

df_prod["Quantidade_ton"] = df_prod["Quantidade"] / 1000

df_prod["Ton_por_Hora"] = df_prod.apply(
    lambda r: r["Quantidade_ton"] / r["Horas"] if r["Horas"] > 0 else 0,
    axis=1
)

df_prod["Desvio_Producao"] = df_prod["Ton_por_Hora"].apply(
    lambda x: max(45 - x, 0)
)

perda_producao_total = df_prod["Desvio_Producao"].sum()

# =========================================================
# TRANSPORTE
# =========================================================

VEICULOS = {
    "RYD8F51": {"viagens": 5, "capacidade": 16.5},
    "CZB8A96": {"viagens": 4, "capacidade": 30},
    "RWJ8J74": {"viagens": 4, "capacidade": 30},
    "RYD8I11": {"viagens": 5, "capacidade": 16.5},
    "SMF2D38": {"viagens": 5, "capacidade": 16.5},
    "RYL1D34": {"viagens": 5, "capacidade": 16.5},
    "SMC9C32": {"viagens": 5, "capacidade": 16.5},
    "RYD8B61": {"viagens": 5, "capacidade": 16.5},
    "QIZ3429": {"viagens": 4, "capacidade": 30},
    "RYL1D14": {"viagens": 5, "capacidade": 16.5},
    "EJV6A02": {"viagens": 4, "capacidade": 30},
}

df_ent["Placa Veículo"] = df_ent["Placa Veículo"].astype(str).str.strip()
df_ent["Cód.Viagem Tpt."] = df_ent["Cód.Viagem Tpt."].astype(str).str.strip()
df_ent["Dia"] = df_ent["Data Transação"].dt.date

viagens_dia = (
    df_ent.groupby(["Dia", "Placa Veículo"])["Cód.Viagem Tpt."]
    .nunique()
    .reset_index(name="Realizadas")
)

perdas_detalhadas = []

for _, row in viagens_dia.iterrows():
    placa = row["Placa Veículo"]
    realizadas = row["Realizadas"]
    dia = row["Dia"]

    if placa in VEICULOS:
        possiveis = VEICULOS[placa]["viagens"]
        capacidade = VEICULOS[placa]["capacidade"]
        perda_dia = max(possiveis - realizadas, 0) * capacidade

        perdas_detalhadas.append({
            "Dia": dia,
            "Placa": placa,
            "Realizadas": realizadas,
            "Perda_Dia (ton)": perda_dia
        })

df_perdas_transporte = pd.DataFrame(perdas_detalhadas)

resumo_transporte = (
    df_perdas_transporte.groupby("Placa")
    .agg({
        "Perda_Dia (ton)": "sum",
        "Realizadas": "sum"
    })
    .reset_index()
)

perda_transporte_total = resumo_transporte["Perda_Dia (ton)"].sum()

# =========================================================
# PERCENTUAIS
# =========================================================

perda_total = perda_producao_total + perda_transporte_total

perc_producao = (perda_producao_total / perda_total) * 100 if perda_total > 0 else 0
perc_transporte = (perda_transporte_total / perda_total) * 100 if perda_total > 0 else 0

# =========================================================
# DASHBOARD
# =========================================================

st.subheader("Totais Gerais")

col1, col2, col3 = st.columns(3)
col1.metric("Programado (ton)", f"{prog_total:,.2f}")
col2.metric("Produzido (ton)", f"{prod_total:,.2f}")
col3.metric("Entregue (ton)", f"{ent_total:,.2f}")

st.divider()

col4, col5 = st.columns(2)
col4.metric("Perda Produção (ton)", f"{perda_producao_total:,.2f}", f"{perc_producao:.1f}%")
col5.metric("Perda Transporte (ton)", f"{perda_transporte_total:,.2f}", f"{perc_transporte:.1f}%")

st.divider()

# 🔹 GRÁFICO AGORA ANTES DO DATAFRAME DE PRODUÇÃO
st.subheader("Entregas por Dia")
ent_daily = df_ent.groupby("Dia")["Total (Kg)"].sum() / 1000
st.line_chart(ent_daily)

st.divider()

st.subheader("Produção")
st.dataframe(
    df_prod[[
        "Data",
        "Inicial",
        "Final",
        "Quantidade_ton",
        "Horas",
        "Ton_por_Hora",
        "Desvio_Producao"
    ]],
    use_container_width=True
)

st.divider()

st.subheader("Caminhões")

st.dataframe(resumo_transporte, use_container_width=True)
