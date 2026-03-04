from supabase.client import create_client
import streamlit as st
import pandas as pd

url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["service_key"]
supabase = create_client(url, key)


st.set_page_config(page_title="Indicadores Ração SDR", layout="wide")
st.title("Painel de desvios - Ração Sidrolândia")

# =========================================================
# UPLOAD DAS 3 PLANILHAS
# =========================================================

st.sidebar.header("Upload das Planilhas")

arquivo_prog = st.sidebar.file_uploader("Programacao.xlsx", type=["xlsx"])
arquivo_prod = st.sidebar.file_uploader("Producao.xlsx", type=["xlsx"])
arquivo_ent = st.sidebar.file_uploader("Entregas.xlsx", type=["xlsx"])
res = supabase.table("entregas").select("*").limit(1).execute()
st.write(res.data)

if arquivo_prog and arquivo_prod and arquivo_ent:
    df_prog = pd.read_excel(arquivo_prog)
    df_prod = pd.read_excel(arquivo_prod)
    df_ent = pd.read_excel(arquivo_ent)

    # Limpar espaços extras dos nomes das colunas
    df_prog.columns = df_prog.columns.str.strip()
    df_prod.columns = df_prod.columns.str.strip()
    df_ent.columns = df_ent.columns.str.strip()

    # Persistir no Supabase com upsert
    supabase.table("programacao").upsert(
        df_prog.to_dict(orient="records"),
        on_conflict=["Data Pedido", "Cliente"]  # ajuste conforme suas colunas únicas
    ).execute()

    supabase.table("producao").upsert(
        df_prod.to_dict(orient="records"),
        on_conflict=["Data", "Ração"]  # ajuste conforme suas colunas únicas
    ).execute()

    supabase.table("entregas").upsert(
        df_ent.to_dict(orient="records"),
        on_conflict=["Data Transação", "Placa Veículo", "Cód.Viagem Tpt."]  # ajuste conforme suas colunas únicas
    ).execute()
else:
    st.warning("Envie as 3 planilhas para continuar.")
    st.stop()
res_prog = supabase.table("programacao").select("*").execute()
df_prog = pd.DataFrame(res_prog.data)

res_prod = supabase.table("producao").select("*").execute()
df_prod = pd.DataFrame(res_prod.data)

res_ent = supabase.table("entregas").select("*").execute()
df_ent = pd.DataFrame(res_ent.data)

# =========================================================
# DATAS
# =========================================================

df_prog["Data Pedido"] = pd.to_datetime(df_prog["Data Pedido"], errors="coerce")
df_prod["Data"] = pd.to_datetime(df_prod["Data"], errors="coerce")
df_ent["Data Transação"] = pd.to_datetime(df_ent["Data Transação"], errors="coerce")

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
# CONVERSÃO PARA NUMÉRICOS
# =========================================================

df_prog["Quantidade Pedido"] = pd.to_numeric(df_prog["Quantidade Pedido"], errors="coerce").fillna(0)
df_prod["Quantidade"] = pd.to_numeric(df_prod["Quantidade"], errors="coerce").fillna(0)
df_ent["Total (Ton)"] = pd.to_numeric(df_ent["Total (Kg)"], errors="coerce").fillna(0)

prog_total = df_prog["Quantidade Pedido"].sum() / 1000
prod_total = df_prod["Quantidade"].sum() / 1000
ent_total = df_ent["Total (Ton)"].sum() / 1000

# =========================================================
# PRODUÇÃO
# =========================================================

df_prod["Inicial_dt"] = pd.to_datetime(
    df_prod["Data"].astype( str) + " " + df_prod["Inicial"].astype(str),
    errors="coerce"
)
df_prod["Final_dt"] = pd.to_datetime(
    df_prod["Data"].astype(str) + " " + df_prod["Final"].astype(str),
    errors="coerce"
)
df_prod["Ração"] = (df_prod["Ração"])
df_prod["Horas"] = ((df_prod["Final_dt"] - df_prod["Inicial_dt"]).dt.total_seconds() / 3600)
df_prod["Quantidade_ton"] = df_prod["Quantidade"] / 1000
df_prod["Ton_por_Hora"] = df_prod.apply(lambda r: r["Quantidade_ton"] / r["Horas"] if r["Horas"] > 0 else 0, axis=1)
df_prod["Desvio_Producao"] = df_prod["Ton_por_Hora"].apply(lambda x: max(45 - x, 0))
perda_producao_total = df_prod["Desvio_Producao"].sum()

# =========================================================
# TRANSPORTE
# =========================================================

VEICULOS = {
    "RYD8F51": {"viagens": 5, "capacidade": 16.5},
    "CZB8A96": {"viagens": 4, "capacidade": 30},
    "RWJ8J74": {"viagens": 4, "capacidade": 26},
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
dias_unicos = df_ent["Dia"].unique()

for dia in dias_unicos:
    for placa, info in VEICULOS.items():
        # viagens realizadas nesse dia para essa placa
        realizadas = viagens_dia[
            (viagens_dia["Dia"] == dia) & (viagens_dia["Placa Veículo"] == placa)
        ]["Realizadas"].sum()

        possiveis = info["viagens"]
        capacidade = info["capacidade"]

        # calcula desvios
        desvio_viagens = max(possiveis - realizadas, 0)
        desvio_ton = desvio_viagens * capacidade

        perdas_detalhadas.append({
            "Dia": dia,
            "Placa": placa,
            "Desvio_Viagens": desvio_viagens,
            "Perda_Dia (ton)": desvio_ton
        })

df_perdas_transporte = pd.DataFrame(perdas_detalhadas)

# resumo por placa
resumo_transporte = (
    df_perdas_transporte.groupby("Placa")
    .agg({
        "Desvio_Viagens": "sum",
        "Perda_Dia (ton)": "sum"
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
# Mostrar período selecionado no topo
if data_inicio == data_fim:
    periodo_str = f"{data_inicio.strftime('%d/%m/%Y')}"
else:
    periodo_str = f"{data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"

# Espaço antes e depois + destaque
st.markdown("<br>", unsafe_allow_html=True)  # espaço antes
st.markdown(
    f"<h4 style='text-align:center; color:darkorange;'>Período selecionado: {periodo_str}</h4>",
    unsafe_allow_html=True
)
st.markdown("<br>", unsafe_allow_html=True)  # espaço depois
st.markdown("<br>", unsafe_allow_html=True)

st.subheader("Totais Gerais")
col1, col2, col3 = st.columns(3)
col1.metric("Programado (ton)", f"{prog_total:,.2f}")
col2.metric("Produzido (ton)", f"{prod_total:,.2f}")
col3.metric("Entregue (ton)", f"{ent_total:,.2f}")

st.divider()
col4, col5 = st.columns(2)
col4.metric(
    "Perda Produção",
    f"{perda_producao_total:,.2f} ton",
    f"{perc_producao:.1f}%",
    delta_color="inverse"  # vermelho se negativo, verde se positivo
)

col5.metric(
    "Perda Transporte",
    f"{perda_transporte_total:,.2f} ton",
    f"{perc_transporte:.1f}%",
    delta_color="inverse"   # verde se positivo
)


st.divider()
st.subheader("Entregas por Dia")

# Agrupar por dia e somar
ent_daily = df_ent.groupby("Dia")["Total (Ton)"].sum().reset_index()

# Converter coluna para datetime
ent_daily["Dia"] = pd.to_datetime(ent_daily["Dia"])

# Ordenar cronologicamente
ent_daily = ent_daily.sort_values("Dia")

# Criar coluna formatada para exibição
ent_daily["Dia_fmt"] = ent_daily["Dia"].dt.strftime("%d/%m")

# Gráfico usando coluna formatada como eixo X
st.line_chart(ent_daily.set_index("Dia_fmt")["Total (Ton)"] / 1000)







st.divider()
st.subheader("Produção")
df_prod_display = df_prod.copy() 
df_prod_display["Data"] = df_prod_display["Data"].dt.date
st.dataframe(
    df_prod_display[["Data", "Inicial", "Final","Ração", "Quantidade_ton", "Horas", "Ton_por_Hora", "Desvio_Producao"]],
    use_container_width=True
)

st.divider()
st.subheader("Caminhões")
st.dataframe(resumo_transporte, use_container_width=True)
df_chart = resumo_transporte.set_index("Placa")[["Perda_Dia (ton)"]] 
df_chart = df_chart.sort_values(by="Perda_Dia (ton)", ascending=True) 
st.bar_chart(df_chart)



