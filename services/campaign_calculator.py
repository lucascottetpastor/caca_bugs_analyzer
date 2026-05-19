import pandas as pd

PRIORITY_VALUES = {
    'Urgente': 100.0,   # Hotfix visão Aluno
    'Alta':    50.0,    # Hotfix visão Gestor
    'Média':   25.0,    # BugFix
    'Baixa':   0.0,     # Melhoria
}

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
    """"
    Gera o relatorio consolidado da campanha

    Args:
        df: DataFrame bruto (aba "Todos os tickets")

    Returns:
        DataFrame com colunas:
            - Proprietário do ticket -> str
            - Total BUGs -> int
            - Positivo -> float
            - Negativo -> float 
            - Saldo -> float
    """

    # garantia que todas colunas existem!
    validate_columns(df)

    eligible = filter_teams(df)

    eligible["valor"] = eligible.apply(calculate_ticket_value, axis=1)

    eligible["positivo"] = eligible["valor"].where(eligible["valor"] > 0, 0)
    eligible["negativo"] = eligible["valor"].where(eligible["valor"] < 0, 0)

    report = eligible.groupby("Proprietário do ticket").agg(
        total_bugs = pd.NamedAgg(column="valor", aggfunc="count"),
        positivo = pd.NamedAgg(column="positivo", aggfunc="sum"),
        negativo = pd.NamedAgg(column="negativo", aggfunc="sum"),
    ).reset_index()

    report["saldo"] = report["positivo"] + report["negativo"]

    report = report.sort_values(by="saldo", ascending=False).reset_index(drop=True)

    return report

