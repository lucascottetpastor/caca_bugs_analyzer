import pandas as pd

PRIORITY_VALUES = {
    'Urgente': 100.0,   # Hotfix visão Aluno
    'Alta':    50.0,    # Hotfix visão Gestor
    'Média':   25.0,    # BugFix
    'Baixa':   0.0,     # Melhoria
}

IGNORED_STATUS = [
    'Solicitação'
    ]

INFORMATIVE_PRIORITY = 'Baixa'

NOT_A_BUG_STATUS = 'Não é bug'
NOT_A_BUG_PENALTY = -200.0

# status de workflow usados nos KPIs
RESOLVED_STATUS = 'Deploy (resolvido)'
AWAITING_DEPLOY_STATUS = 'Aguardando deploy'

# minimo de bugs validos (bugfix/hotfix) para o colaborador qualificar na campanha
MIN_VALID_BUGS = 5

ELIGIBLE_TEAM = 'Atendimento'

REQUIRED_COLUMNS = [
    'Equipes atribuídas',
    'Status do ticket',
    'Prioridade',
    'Proprietário do ticket',
]

def list_sheet_names(file) -> list[str]:
    """
    Lista os nomes das abas de uma planilha Excel.
    
    Args:
        file: caminho do arquivo OU objeto de arquivo (uploaded_file do Streamlit).
    
    Returns:
        Lista de strings com nomes das abas, na ordem que aparecem no Excel.
    """
    return pd.ExcelFile(file).sheet_names

def read_sheet(file, sheet_name: str) -> pd.DataFrame:
    """
    Lê uma aba específica de uma planilha Excel e retorna um DataFrame.
    
    Args:
        file: caminho do arquivo OU objeto de arquivo (uploaded_file do Streamlit).
        sheet_name: nome da aba a ser lida.
    
    Returns:
        DataFrame contendo os dados da aba especificada.
    """
    return pd.read_excel(file, sheet_name=sheet_name)

def validate_columns(df: pd.DataFrame) -> None:
    """"
    Garante que o DataFrame contém todas as colunas necessárias para a campanha.

    Raises:
        ValueError: Se alguma das colunas obrigatórias estiver faltando, listsa as faltatantes.
    """

    missing = []

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            missing.append(column)
    if missing:
        raise ValueError(
            f"Colunas obrigatórias faltando: {', '.join(missing)}"
            f"Verifique se a planilha contém as seguintes colunas: {', '.join(REQUIRED_COLUMNS)}"
            )
    
def calculate_ticket_value(row: pd.Series) -> float:
    """
    Calcula o valor de 1 ticket.

    Args: 
        row: 1 unica linha do DataFrame

    Returns:
        Valor em Reais:
            - Penalidade negativa se for "não é bug"
            - Valor positivo conforme a prioridade
            - 0.0 se a prioridade não estiver no mapa de valores
    """
    
    priority = row["Prioridade"]

    # caso especial: "Não é bug" com prioridade Baixa não gera penalidade
    if row["Status do ticket"] == NOT_A_BUG_STATUS and priority == INFORMATIVE_PRIORITY:
        return 0.0

    if row["Status do ticket"] == NOT_A_BUG_STATUS:
        return NOT_A_BUG_PENALTY

    return PRIORITY_VALUES.get(priority, 0.0)

def filter_teams(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna somente tickets que são do time Atendimento.
    Apenas time de atendimento partipando da campanha
    """

    return df[df['Equipes atribuídas'] == ELIGIBLE_TEAM].copy()

def calculate_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera o relatorio consolidado da campanha

    Args:
        df: DataFrame bruto (aba "Todos os tickets")

    Returns:
        DataFrame com colunas:
            - Proprietário do ticket -> str
            - total_cards -> int       (total de cards criados)
            - bugs_validos -> int      (bugfix/hotfix, com valor positivo)
            - baixa_prioridade -> int  (tickets de prioridade Baixa, informativos)
            - nao_e_bug -> int         ("Não é bug" exceto prioridade Baixa)
            - positivo -> float        (saldo positivo)
            - negativo -> float        (saldo negativo)
            - saldo -> float           (saldo final)
    """

    COLUNAS_REPORT = [
        "Proprietário do ticket", "total_cards", "bugs_validos",
        "baixa_prioridade", "nao_e_bug", "positivo", "negativo", "saldo",
    ]

    # todas colunas existem
    validate_columns(df)

    # remove tickets sem proprietario ou sem prioridade
    eligible = remove_invalid_tickets(df)

    if eligible.empty:
        return pd.DataFrame(columns=COLUNAS_REPORT)

    eligible = eligible.copy()

    # classificacao de cada ticket
    is_baixa = eligible["Prioridade"] == INFORMATIVE_PRIORITY
    is_nao_bug = eligible["Status do ticket"] == NOT_A_BUG_STATUS
    is_ignorado = eligible["Status do ticket"].isin(IGNORED_STATUS)

    # valor de cada ticket; tickets que nao entram no saldo (Baixa ou status
    # ignorado) sao zerados
    eligible["valor"] = eligible.apply(calculate_ticket_value, axis=1)
    eligible.loc[is_baixa | is_ignorado, "valor"] = 0.0

    eligible["positivo"] = eligible["valor"].where(eligible["valor"] > 0, 0)
    eligible["negativo"] = eligible["valor"].where(eligible["valor"] < 0, 0)

    # flags de contagem por categoria
    eligible["_total"] = 1
    eligible["_bug_valido"] = (eligible["valor"] > 0).astype(int)
    eligible["_baixa"] = is_baixa.astype(int)
    eligible["_nao_e_bug"] = (is_nao_bug & ~is_baixa).astype(int)

    report = eligible.groupby("Proprietário do ticket").agg(
        total_cards = pd.NamedAgg(column="_total", aggfunc="sum"),
        bugs_validos = pd.NamedAgg(column="_bug_valido", aggfunc="sum"),
        baixa_prioridade = pd.NamedAgg(column="_baixa", aggfunc="sum"),
        nao_e_bug = pd.NamedAgg(column="_nao_e_bug", aggfunc="sum"),
        positivo = pd.NamedAgg(column="positivo", aggfunc="sum"),
        negativo = pd.NamedAgg(column="negativo", aggfunc="sum"),
    ).reset_index()

    report["saldo"] = report["positivo"] + report["negativo"]

    report = report[COLUNAS_REPORT]
    report = report.sort_values(by="saldo", ascending=False).reset_index(drop=True)

    return report

def calculate_kpis(df: pd.DataFrame) -> dict:
    """
    Conta os bugs validos por categoria de prioridade, para os KPIs do topo.

    Args:
        df: DataFrame ja filtrado

    Returns:
        dicionario com as contagens:
            - bugs_validos -> int      (total Urgente + Alta + Média validos)
            - hotfix_aluno -> int      (prioridade Urgente)
            - hotfix_gestor -> int     (prioridade Alta)
            - bugfix -> int            (prioridade Média)
            - resolvidos -> int        (status "Deploy (resolvido)")
            - aguardando_deploy -> int (status "Aguardando deploy")
    """

    vazio = {
        "bugs_validos": 0, "hotfix_aluno": 0, "hotfix_gestor": 0,
        "bugfix": 0, "resolvidos": 0, "aguardando_deploy": 0,
    }

    validate_columns(df)

    eligible = remove_invalid_tickets(df)
    if eligible.empty:
        return vazio

    eligible = eligible.copy()

    is_baixa = eligible["Prioridade"] == INFORMATIVE_PRIORITY
    is_ignorado = eligible["Status do ticket"].isin(IGNORED_STATUS)

    # valor zera para Baixa e status ignorado; bug valido tem valor positivo
    eligible["valor"] = eligible.apply(calculate_ticket_value, axis=1)
    eligible.loc[is_baixa | is_ignorado, "valor"] = 0.0

    # conta por prioridade apenas os bugs validos (valor > 0)
    validos = eligible[eligible["valor"] > 0]
    por_prioridade = validos["Prioridade"].value_counts()

    hotfix_aluno = int(por_prioridade.get("Urgente", 0))
    hotfix_gestor = int(por_prioridade.get("Alta", 0))
    bugfix = int(por_prioridade.get("Média", 0))

    # contagem por status de workflow
    status = eligible["Status do ticket"]
    resolvidos = int((status == RESOLVED_STATUS).sum())
    aguardando_deploy = int((status == AWAITING_DEPLOY_STATUS).sum())

    return {
        "bugs_validos": hotfix_aluno + hotfix_gestor + bugfix,
        "hotfix_aluno": hotfix_aluno,
        "hotfix_gestor": hotfix_gestor,
        "bugfix": bugfix,
        "resolvidos": resolvidos,
        "aguardando_deploy": aguardando_deploy,
    }

# filtro de mes
def filter_by_month(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
    """
    Filtra os tickets, mantendo somente os criados no mês especificado.

    Args:
        df: DataFrame com os tickets (precisa da coluna "Data de criação")
        month: mês desejado
        year: ano desejado

    Returns:
        DataFrame apenas com os tickets criados no mês/ano especificado.
    """

    # garantia da coluna data é tipo DataTime
    datas = pd.to_datetime(df["Data de criação"], errors='coerce')

    mascara = (datas.dt.month == month) & (datas.dt.year == year)
    return df[mascara].copy()

def get_available_months(df: pd.DataFrame) -> list[tuple[int, int]]:
    """
    Retorna a lista de (ano, mês) que existem na planilha, do mais recente
    para o mais antigo. Serve para popular o seletor de mês na interface.
    """
    datas = pd.to_datetime(df['Data de criação'], errors='coerce')
    
    # remove datas invalidas e extrai pares (ano, mês) únicos
    periodos = datas.dropna().dt.to_period('M').unique()
    
    resultado = [(p.year, p.month) for p in sorted(periodos, reverse=True)]
    return resultado

def remove_invalid_tickets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove tickets que não têm proprietário ou prioridade preenchidos.
    Esses tickets não podem ser atribuídos a ninguém no relatório.
    """
    return df.dropna(subset=['Proprietário do ticket', 'Prioridade']).copy()

def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Aplica filtros de multi-seleção ao DataFrame.

    Args:
        df: DataFrame com os tickets
        filters: dicionario onde a chave e o nome da coluna e o valor
        e uma lista de valores aceitos. Se a lista estiver vazia
        ou for None, o filtro daquela coluna e ignorado.

    Returns:
        DataFrame filtrado com apenas os tickets que casam com todos os filtros.
    """
    resultado = df

    for coluna, valores in filters.items():
        # filtros vazios sao ignorados (equivale a "todos")
        if not valores:
            continue
        resultado = resultado[resultado[coluna].isin(valores)]

    return resultado.copy()