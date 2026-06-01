import streamlit as st

from services.campaign_calculator import (calculate_report, read_sheet, list_sheet_names, filter_by_month, get_available_months, apply_filters, calculate_kpis, MIN_VALID_BUGS)

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

# carrega o css customizado (acentos Zoom sobre o tema nativo do Streamlit)
def load_css(path: str) -> None:
    with open(path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("assets/style.css")

st.title("🐞 Caça aos Bugs - Analyzer")

# passo 1 - upload
with st.container(border=True, key="passo-upload"):
    st.subheader("1️⃣ Envie a planilha")
    uploaded_file = st.file_uploader(
        "Selecione a planilha (.xlsx)",
        type=["xlsx"],
        help="Exporte a planilha do Pipeline de BUGs do HubSpot e faça upload aqui.",
    )

if uploaded_file is None:
    st.info("👆 Aguardando upload da planilha para começar a análise.")
    st.stop()

# passo 2 - aba da planilha
with st.container(border=True, key="passo-aba"):
    st.subheader("2️⃣ Escolha a aba")
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

    # passo 3 - filtros em linha horizontal
    with st.container(border=True, key="passo-filtros"):
        st.subheader("3️⃣ Filtre os dados")
        col_mes, col_equipe, col_prioridade, col_proprietario = st.columns(4)

        with col_mes:
            selected_month_index = st.selectbox(
                "Mês",
                options=range(len(meses_disponiveis)),
                format_func=lambda i: f"{MESES_PT[meses_disponiveis[i][1]]}/{meses_disponiveis[i][0]}",
                help="Define o período da campanha. Apenas os meses presentes na planilha aparecem aqui.",
            )
        selected_year, selected_month = meses_disponiveis[selected_month_index]

        # filtra por mes primeiro, os demais mostram so o que existe no mes
        df_mes = filter_by_month(df, year=selected_year, month=selected_month)

        with col_equipe:
            equipe_selecionada = st.multiselect(
                "Equipe",
                options=df_mes["Equipes atribuídas"].dropna().unique().tolist(),
                help="Selecione uma ou mais equipes. Deixe vazio para incluir todas.",
            )
        with col_prioridade:
            prioridade_selecionada = st.multiselect(
                "Prioridade",
                options=df_mes["Prioridade"].dropna().unique().tolist(),
                help="Selecione uma ou mais prioridades. Deixe vazio para incluir todas.",
            )
        with col_proprietario:
            proprietario_selecionado = st.multiselect(
                "Proprietário",
                options=df_mes["Proprietário do ticket"].dropna().unique().tolist(),
                help="Selecione um ou mais proprietários. Deixe vazio para incluir todos.",
            )

    filtros = {
        "Equipes atribuídas": equipe_selecionada,
        "Prioridade": prioridade_selecionada,
        "Proprietário do ticket": proprietario_selecionado,
    }

    df_filtered = apply_filters(df_mes, filtros)

    if df_filtered.empty:
        st.warning("Nenhum ticket corresponde aos filtros selecionados.")
        st.stop()

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

    # KPIs reativos (recalculam conforme os filtros)
    kpis = calculate_kpis(df_filtered)

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("Bugs Válidos", kpis["bugs_validos"])
    kpi2.metric("HotFix Visão Aluno", kpis["hotfix_aluno"])
    kpi3.metric("HotFix visão Gestor", kpis["hotfix_gestor"])
    kpi4.metric("BugFix", kpis["bugfix"])
    kpi5.metric("Resolvidos", kpis["resolvidos"])
    kpi6.metric("Aguardando Deploy", kpis["aguardando_deploy"])

    st.subheader("📊 Relatório Consolidado")

    COLUNAS_PT = {
        "Proprietário do ticket": "Proprietário",
        "total_cards": "Total de Cards Criados",
        "bugs_validos": "Bugs Válidos (bugfix/hotfix)",
        "baixa_prioridade": "Baixa Prioridade",
        "nao_e_bug": "Não é Bug (exceto Baixa)",
        "positivo": "Saldo Positivo",
        "negativo": "Saldo Negativo",
        "saldo": "Saldo Final (R$)",
    }
    report_display = report.rename(columns=COLUNAS_PT)

    col_bugs = COLUNAS_PT["bugs_validos"]

    def destacar_minimo(valor):
        # colaboradores com menos de MIN_VALID_BUGS bugs validos nao qualificam
        if valor < MIN_VALID_BUGS:
            return "background-color: #FECACA; color: #991B1B; font-weight: bold;"
        return ""

    colunas_saldo = ["Saldo Positivo", "Saldo Negativo", "Saldo Final (R$)"]

    styled = (
        report_display.style
        .map(destacar_minimo, subset=[col_bugs])
        .format("{:.2f}", subset=colunas_saldo)
    )

    st.dataframe(styled, width="stretch", hide_index=True)
    st.caption(
        f"🔴 Bugs Válidos em vermelho: menos de {MIN_VALID_BUGS} bugs válidos\n"
        f"(bugfix/hotfix) no período — colaborador não qualifica na campanha."
    )

except ValueError as e:
    # erros de validacao dos dados
    st.error(f"Error: {str(e)}")

except Exception as e:
    # qualquer outro erro
    st.error(f"Error inesperado: {str(e)}")
    st.exception(e)