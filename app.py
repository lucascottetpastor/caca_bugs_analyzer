import html

import streamlit as st

from services.campaign_calculator import (calculate_report, read_sheet, list_sheet_names, filter_by_month, get_available_months, apply_filters, calculate_kpis, classify_bug_type, BUG_TYPE_CATEGORIES, MIN_VALID_BUGS)

# cores das badges de prioridade no kanban
PRIORITY_COLORS = {
    "Urgente": "#EF4444",
    "Alta":    "#F59E0B",
    "Média":   "#695A9B",
    "Baixa":   "#06B6D4",
}

# ordem canonica das colunas do quadro kanban 
STATUS_ORDER = [
    "Bug detectado",
    "Backlog de melhorias",
    "em Front-end",
    "em Back-end",
    "em Teste",
    "Aguardando deploy",
    "Deploy resolvido",
    "Não é bug",
    "Solicitação",
]

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

# carrega o css customizado
def load_css(path: str) -> None:
    with open(path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def encontrar_coluna(df, candidatos: list[str]):
    # retorna o primeiro nome de coluna presente no df, ou None
    for nome in candidatos:
        if nome in df.columns:
            return nome
    return None

def format_brl(valor) -> str:
    # formata em moeda BR
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def montar_card(ticket, id_col, nome_col) -> str:
    # monta o html de 1 card de ticket para o kanban
    prioridade = str(ticket.get("Prioridade", "")).strip()
    cor = PRIORITY_COLORS.get(prioridade, "#64748B")
    proprietario = html.escape(str(ticket.get("Proprietário do ticket", "—")))

    partes = ['<div class="kanban-card">']
    if id_col:
        partes.append(f'<div class="kanban-card-id">#{html.escape(str(ticket[id_col]))}</div>')
    if nome_col:
        partes.append(f'<div class="kanban-card-title">{html.escape(str(ticket[nome_col]))}</div>')
    partes.append(
        f'<span class="kanban-badge" style="background:{cor}">'
        f'{html.escape(prioridade) or "—"}</span>'
    )
    partes.append(f'<div class="kanban-card-owner">👤 {proprietario}</div>')
    partes.append("</div>")
    return "".join(partes)

def ordenar_status(df) -> list[str]:
    # define a ordem das colunas: primeiro o fluxo conhecido, depois os extras
    presentes = set(df["Status do ticket"].dropna().unique())
    ordenados = [s for s in STATUS_ORDER if s in presentes]
    extras = sorted(presentes - set(STATUS_ORDER))
    return ordenados + extras

def render_kanban(df_kanban, status_cols: list[str]) -> None:
    # mostra os tickets como cards agrupados por status, em colunas fixas
    st.subheader("🗂️ Tickets por status")
    st.caption(f"{len(df_kanban)} ticket(s) no recorte atual")

    if not status_cols:
        st.info("Sem status para exibir no kanban.")
        return

    id_col = encontrar_coluna(df_kanban, ["Ticket ID", "ID do ticket", "ID"])
    nome_col = encontrar_coluna(df_kanban, ["Nome do ticket", "Assunto", "Título", "Titulo"])

    # colunas fixas: aparecem sempre, mesmo vazias apos filtrar
    colunas_html = []
    for status in status_cols:
        do_status = df_kanban[df_kanban["Status do ticket"] == status]
        cards = "".join(montar_card(t, id_col, nome_col) for _, t in do_status.iterrows())
        if not cards:
            cards = '<div class="kanban-empty">Sem tickets</div>'
        colunas_html.append(
            f'<div class="kanban-col">'
            f'<div class="kanban-col-header">{html.escape(str(status))} '
            f'<span class="count">· {len(do_status)}</span></div>'
            f'<div class="kanban-col-body">{cards}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="kanban-board">{"".join(colunas_html)}</div>',
        unsafe_allow_html=True,
    )

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
        col_mes, col_equipe, col_tipo, col_proprietario = st.columns(4)

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

        # categoria amigavel de Tipo Bug, usada no filtro
        df_mes["Categoria Tipo Bug"] = classify_bug_type(df_mes)

        with col_equipe:
            equipe_selecionada = st.multiselect(
                "Equipe",
                options=df_mes["Equipes atribuídas"].dropna().unique().tolist(),
                help="Selecione uma ou mais equipes. Deixe vazio para incluir todas.",
            )
        with col_tipo:
            categorias = [c for c in BUG_TYPE_CATEGORIES if c in set(df_mes["Categoria Tipo Bug"])]
            tipo_selecionado = st.multiselect(
                "Tipo Bug",
                options=categorias,
                help="Selecione um ou mais tipos de bug. Deixe vazio para incluir todos.",
            )
        with col_proprietario:
            proprietario_selecionado = st.multiselect(
                "Proprietário",
                options=df_mes["Proprietário do ticket"].dropna().unique().tolist(),
                help="Selecione um ou mais proprietários. Deixe vazio para incluir todos.",
            )

    filtros = {
        "Equipes atribuídas": equipe_selecionada,
        "Categoria Tipo Bug": tipo_selecionado,
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
    kpi3.metric("HotFix Visão Gestor", kpis["hotfix_gestor"])
    kpi4.metric("BugFix", kpis["bugfix"])
    kpi5.metric("Melhoria", kpis["melhoria"])
    kpi6.metric("Resolvidos", kpis["resolvidos"])

    st.subheader("📊 Relatório Consolidado")

    COLUNAS_PT = {
        "Proprietário do ticket": "Proprietário",
        "total_cards": "Total de Cards Criados",
        "bugs_validos": "Bugs Válidos (bugfix/hotfix)",
        "baixa_prioridade": "Baixa Prioridade",
        "melhoria": "Melhoria",
        "nao_e_bug": "Não é Bug (exceto Baixa)",
        "positivo": "Saldo Positivo",
        "negativo": "Saldo Negativo",
        "saldo": "Saldo Final",
    }
    report_display = report.rename(columns=COLUNAS_PT)

    col_bugs = COLUNAS_PT["bugs_validos"]

    def destacar_minimo(valor):
        # colaboradores com menos de MIN_VALID_BUGS bugs validos nao qualificam
        if valor < MIN_VALID_BUGS:
            return "background-color: #FECACA; color: #991B1B; font-weight: bold;"
        return ""

    colunas_saldo = ["Saldo Positivo", "Saldo Negativo", "Saldo Final"]

    styled = (
        report_display.style
        .map(destacar_minimo, subset=[col_bugs])
        .format(format_brl, subset=colunas_saldo)
    )

    st.dataframe(styled, width="stretch", hide_index=True)
    st.caption(
        f"🔴 Bugs Válidos em vermelho: menos de {MIN_VALID_BUGS} bugs válidos\n"
        f"(bugfix/hotfix) no período - colaborador não qualifica na campanha."
    )

    st.divider()
    render_kanban(df_filtered, ordenar_status(df))

except ValueError as e:
    # erros de validacao dos dados
    st.error(f"Error: {str(e)}")

except Exception as e:
    # qualquer outro erro
    st.error(f"Error inesperado: {str(e)}")
    st.exception(e)