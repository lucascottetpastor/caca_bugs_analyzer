import streamlit as st

from services.campaign_calculator import (calculate_report, read_sheet, list_sheet_names, filter_by_month, get_available_months)

MESES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro"
}

# config pagina

st.set_page_config(
    page_title="Caça aos Bugs - Analyzer",
    page_icon="🐞",
    layout="wide",
    )

st.title("🐞 Caça aos Bugs - Analyzer")

# upload 

uploaded_file = st.file_uploader(
    "Selecione a planilha (.xlsx)",
    type=["xlsx"],
    help="Exporte a planilha do Pipeline de BUGs do HubSpot e faça upload aqui.",
    )

if uploaded_file is None:
    st.info("👆 Aguardando upload da planilha para começar a análise.")
    st.stop()

# aba da planilha

sheet_names = list_sheet_names(uploaded_file)
selected_sheet = st.selectbox(
    "Selecione a aba a ser analisada",
    options=sheet_names,
    index=0,
    help="Selecione a aba da planilha que contém os dados dos tickets. Normalmente é a aba 'Todos os Tickets'."
)

try:
    df = read_sheet(uploaded_file, selected_sheet)

    # + filtro de mes
    meses_disponiveis = get_available_months(df)

    if not meses_disponiveis:
        st.warning("A planilha não contém datas de criação válidas para filtrar.")
        st.stop()

    selected_month_index = st.selectbox(
        "Selecione o mês da campanha",
        options=range(len(meses_disponiveis)),
        format_func=lambda i: f"{MESES_PT[meses_disponiveis[i][1]]}/{meses_disponiveis[i][0]}",
        help="Apenas os meses presentes na planilha aparecem aqui.",
    )
    selected_year, selected_month = meses_disponiveis[selected_month_index]

    df_filtered = filter_by_month(df, year=selected_year, month=selected_month)

    # processar + exibir
    report = calculate_report(df_filtered)

    if len(report) == 0:
        st.warning(
            f"Nenhum ticket encontrado em {MESES_PT[selected_month]}/{selected_year}."
        )
        st.stop()

    st.success(
        f"Análise de {MESES_PT[selected_month]}/{selected_year} concluída! "
        f"{len(report)} colaborador(es) encontrado(s) no relatório."
    )

    st.subheader("📊 Relatório Consolidado")
    st.dataframe(report, width="stretch", hide_index=True)

except ValueError as e:
    # erros de validacao dos dados
    st.error(f"Error: {str(e)}")

except Exception as e:
    # qualquer outro erro
    st.error(f"Error inesperado: {str(e)}")
    st.exception(e)