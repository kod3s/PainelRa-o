from supabase import create_client
import streamlit as st
import pandas as pd

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
# FUNÇÃO SEGURA PARA JSON
# =========================
def preparar_df(df):
    df.columns = df.columns.str.strip()

    # Converter datetime para string ISO
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")

    # Converter qualquer objeto date
    df = df.applymap(
        lambda x: x.strftime("%Y-%m-%d")
        if hasattr(x, "strftime")
        else x
    )

    df = df.where(pd.notnull(df), None)

    return df


# =========================
# UPLOAD PARA O BANCO
# =========================
if arquivo_prog and arquivo_prod and arquivo_ent:

    # PROGRAMACAO
    df_prog = preparar_df(pd.read_excel(arquivo_prog))

    df_prog = df_prog.rename(columns={
        "Data Pedido": "data_pedido",
        "Quantidade Pedido": "quantidade_pedido"
    })

    df_prog = df_prog.dropna(subset=["data_pedido"])

    if not df_prog.empty:
        try:
            supabase.table("programacao").upsert(
                df_prog.to_dict(orient="records"),
                on_conflict="data_pedido"
            ).execute()
        except Exception as e:
            st.error(f"Erro programacao: {e}")
            st.stop()

    # PRODUCAO
    df_prod = preparar_df(pd.read_excel(arquivo_prod))

    df_prod = df_prod.rename(columns={
        "Data": "data",
        "Inicial": "inicial",
        "Final": "final",
        "Quantidade": "quantidade"
    })

    df_prod = df_prod.dropna(subset=["data"])

    if not df_prod.empty:
        try:
            supabase.table("producao").upsert(
                df_prod.to_dict(orient="records"),
                on_conflict="data,inicial,final"
            ).execute()
        except Exception as e:
            st.error(f"Erro producao: {e}")
            st.stop()

    # ENTREGAS
    df_ent = preparar_df(pd.read_excel(arquivo_ent))

    df_ent = df_ent.rename(columns={
        "Data Transação": "data_transacao",
        "Placa Veículo": "placa_veiculo",
        "Cód.Viagem Tpt.": "cod_viagem",
        "Total (Kg)": "total_kg"
    })

    df_ent = df_ent.dropna(subset=["data_transacao"])

    if not df_ent.empty:
        try:
            supabase.table("entregas").upsert(
                df_ent.to_dict(orient="records"),
                on_conflict="data_transacao,placa_veiculo,cod_viagem"
            ).execute()
        except Exception as e:
            st.error(f"Erro entregas: {e}")
            st.stop()

else:
    st.warning("Envie as 3 planilhas para continuar.")
    st.stop()


# =========================
# BUSCAR DO BANCO
# =========================
df_prog = pd.DataFrame(supabase.table("programacao").select("*").execute().data or [])
df_prod = pd.DataFrame(supabase.table("producao").select("*").execute().data or [])
df_ent = pd.DataFrame(supabase.table("entregas").select("*").execute().data or [])

if df_prog.empty or df_prod.empty or df_ent.empty:
    st.warning("Banco ainda sem dados.")
    st.stop()


# =========================
# CONVERTER DATAS
# =========================
df_prog["data_pedido"] = pd.to_datetime(df_prog["data_pedido"], errors="coerce")
df_prod["data"] = pd.to_datetime(df_prod["data"], errors="coerce")
df_ent["data_transacao"] = pd.to_datetime(df_ent["data_transacao"], errors="coerce")


# =========================
# FILTRO DE PERÍODO
# =========================
st.subheader("Filtro de Período")

data_min = df_ent["data_transacao"].min()
data_max = df_ent["data_transacao"].max()

data_inicio, data_fim = st.date_input(
    "Selecione o período",
    [data_min, data_max]
)

df_prog = df_prog[
    (df_prog["data_pedido"] >= pd.to_datetime(data_inicio)) &
    (df_prog["data_pedido"] <= pd.to_datetime(data_fim))
]

df_prod = df_prod[
    (df_prod["data"] >= pd.to_datetime(data_inicio)) &
    (df_prod["data"] <= pd.to_datetime(data_fim))
]

df_ent = df_ent[
    (df_ent["data_transacao"] >= pd.to_datetime(data_inicio)) &
    (df_ent["data_transacao"] <= pd.to_datetime(data_fim))
]


# =========================
# NUMÉRICOS
# =========================
df_prog["quantidade_pedido"] = pd.to_numeric(df_prog["quantidade_pedido"], errors="coerce").fillna(0)
df_prod["quantidade"] = pd.to_numeric(df_prod["quantidade"], errors="coerce").fillna(0)
df_ent["total_kg"] = pd.to_numeric(df_ent["total_kg"], errors="coerce").fillna(0)

prog_total = df_prog["quantidade_pedido"].sum() / 1000
prod_total = df_prod["quantidade"].sum() / 1000
ent_total = df_ent["total_kg"].sum() / 1000


# =========================
# PRODUÇÃO
# =========================
df_prod["inicial_dt"] = pd.to_datetime(
    df_prod["data"].astype(str) + " " + df_prod["inicial"].astype(str),
    errors="coerce"
)

df_prod["final_dt"] = pd.to_datetime(
    df_prod["data"].astype(str) + " " + df_prod["final"].astype(str),
    errors="coerce"
)

df_prod["horas"] = (
    (df_prod["final_dt"] - df_prod["inicial_dt"])
    .dt.total_seconds()
    .div(3600)
)

df_prod["horas"] = df_prod["horas"].replace(0, None)

df_prod["quantidade_ton"] = df_prod["quantidade"] / 1000
df_prod["ton_por_hora"] = df_prod["quantidade_ton"] / df_prod["horas"]

df_prod["desvio_producao"] = df_prod["ton_por_hora"].apply(
    lambda x: max(45 - x, 0) if pd.notnull(x) else 0
)

perda_producao_total = df_prod["desvio_producao"].sum()


# =========================
# DASHBOARD
# =========================
st.subheader("Totais Gerais")

col1, col2, col3 = st.columns(3)
col1.metric("Programado (ton)", f"{prog_total:,.2f}")
col2.metric("Produzido (ton)", f"{prod_total:,.2f}")
col3.metric("Entregue (ton)", f"{ent_total:,.2f}")

st.divider()

st.metric("Perda Produção (ton)", f"{perda_producao_total:,.2f}")

st.divider()

st.subheader("Entregas por Dia")

df_ent["dia"] = df_ent["data_transacao"].dt.date
ent_daily = df_ent.groupby("dia")["total_kg"].sum().reset_index()
ent_daily["dia"] = pd.to_datetime(ent_daily["dia"])
ent_daily = ent_daily.sort_values("dia")
ent_daily["dia_fmt"] = ent_daily["dia"].dt.strftime("%d/%m")

st.line_chart(ent_daily.set_index("dia_fmt")["total_kg"] / 1000)
