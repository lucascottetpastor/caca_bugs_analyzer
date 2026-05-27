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
    
    if row["Status do ticket"] == NOT_A_BUG_STATUS:
        return NOT_A_BUG_PENALTY
    
    priority = row["Prioridade"]
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
            - total_bugs -> int
            - bugs_baixa -> int
            - positivo -> float
            - negativo -> float
            - saldo -> float
    """

    # todas colunas existem
    validate_columns(df)

    eligible = filter_teams(df)

    # remove tickets sem proprietario ou sem prioridade
    eligible = remove_invalid_tickets(eligible)

    # separa os tickets de prioridade Baixa - coluna informativa
    is_baixa = eligible["Prioridade"] == INFORMATIVE_PRIORITY
    baixa_tickets = eligible[is_baixa]

    # demais tickets: remove os status ignorados
    contaveis = eligible[~is_baixa]
    contaveis = contaveis[~contaveis["Status do ticket"].isin(IGNORED_STATUS)]
    contaveis = contaveis.copy()

    contaveis["valor"] = contaveis.apply(calculate_ticket_value, axis=1)

    contaveis["positivo"] = contaveis["valor"].where(contaveis["valor"] > 0, 0)
    contaveis["negativo"] = contaveis["valor"].where(contaveis["valor"] < 0, 0)

    report = contaveis.groupby("Proprietário do ticket").agg(
        total_bugs = pd.NamedAgg(column="Ticket ID", aggfunc="count"),
        positivo = pd.NamedAgg(column="positivo", aggfunc="sum"),
        negativo = pd.NamedAgg(column="negativo", aggfunc="sum"),
    ).reset_index()

    # conta os tickets de Baixa por proprietario
    baixa_count = baixa_tickets.groupby("Proprietário do ticket").size()

    # adiciona a coluna bugs_baixa (0 se a pessoa nao tem nenhum)
    report["bugs_baixa"] = report["Proprietário do ticket"].map(baixa_count).fillna(0).astype(int)

    report["saldo"] = report["positivo"] + report["negativo"]

    report = report[[
        "Proprietário do ticket", "total_bugs", "bugs_baixa",
        "positivo", "negativo", "saldo"
    ]]
    report = report.sort_values(by="saldo", ascending=False).reset_index(drop=True)

    return report

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