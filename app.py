import streamlit as st

from services.campaign_calculator import (calculate_report, read_sheet, list_sheet_names)

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

# processar + exibir

try:
    df = read_sheet(uploaded_file, selected_sheet)
    report = calculate_report(df)

    st.success(f"Análise concluída! {len(report)} colaborador(es) encontrado(s) no relatório.")

    st.subheader("📊 Relatório Consolidado")
    st.dataframe(report, use_container_width=True, hide_index=True)

except ValueError as e:
    # erros de validacao dos dados
    st.error(f"Error: {str(e)}")

except Exception as e:
    # qualquer outro erro
    st.error(f"Error inesperado: {str(e)}")
    st.exception(e)