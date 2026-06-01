""""
Testes para a logica do calculo da campanha

Cada teste cria um DataFrame pequeno fake e valida que o relatorio gerado bate com o esperado pela regra de negocio
"""

import pandas as pd
import pytest

import services.campaign_calculator

def make_ticket(
    ticket_id: str = "1",
    equipe: str = "Atendimento",
    status: str = "em Front-end",
    prioridade: str = "Média",
    proprietario: str = "João"
) -> dict:
    """"
    Cria um ticket fake como dicionario
    """

    return {
        "Ticket ID": ticket_id,
        "Equipes atribuídas": equipe,
        "Status do ticket": status,
        "Prioridade": prioridade,
        "Proprietário do ticket": proprietario
    }



# TESTE 1 - Valores por prioridade

def test_valores_por_prioridade():
    """
    Cada prioridade deve gerar o valor correto:
    Urgente = 100, Alta = 50, Média = 25, Baixa = 0
    """

    tickets = [
        make_ticket(ticket_id="1", prioridade="Urgente"),
        make_ticket(ticket_id="2", prioridade="Alta"),
        make_ticket(ticket_id="3", prioridade="Média"),
        make_ticket(ticket_id="4", prioridade="Baixa"),
    ]

    df = pd.DataFrame(tickets)

    report = services.campaign_calculator.calculate_report(df)

    assert len(report) == 1, "Deve haver apenas 1 colaborador no relatório"

    row = report.iloc[0]
    assert row["total_cards"] == 4
    assert row["bugs_validos"] == 3
    assert row["baixa_prioridade"] == 1
    assert row["nao_e_bug"] == 0
    assert row["positivo"] == 175.0
    assert row["negativo"] == 0.0
    assert row["saldo"] == 175.0

# TESTE 2 - Penalidade de não é bug

def test_penalidade_nao_e_bug():
    """
    Ticket com status "Não é bug" aplica penalidade de -200, independente da prioridade
    """

    tickets = [
        make_ticket(ticket_id="1", prioridade="Urgente", status="em Front-end"),
        make_ticket(ticket_id="2", prioridade="Urgente", status="Não é bug"),
    ]

    df = pd.DataFrame(tickets)

    report = services.campaign_calculator.calculate_report(df)

    row = report.iloc[0]
    assert row["total_cards"] == 2
    assert row["bugs_validos"] == 1
    assert row["nao_e_bug"] == 1
    assert row["positivo"] == 100.0
    assert row["negativo"] == -200.0
    assert row["saldo"] == -100.0

# TESTE 3 - calculate_report nao filtra por equipe (V2)

def test_calculate_report_nao_filtra_por_equipe():
    """
    V2: calculate_report nao filtra mais por equipe.
    Tickets de qualquer time devem aparecer no relatorio.
    """

    tickets = [
        make_ticket(ticket_id="1", equipe="Atendimento", prioridade="Urgente", proprietario="Maria"),
        make_ticket(ticket_id="2", equipe="Tecnologia", prioridade="Urgente", proprietario="Pedro"),
    ]

    df = pd.DataFrame(tickets)

    report = services.campaign_calculator.calculate_report(df)

    assert len(report) == 2, "Ambos colaboradores devem aparecer (sem filtro de equipe)"
    assert set(report["Proprietário do ticket"]) == {"Maria", "Pedro"}

# TESTE 4 - Filtro do mês

def test_filtra_por_mes():
    """
    Apenas tickets do mês/ano informados devem ser considerados
    """

    tickets = [
        {**make_ticket(ticket_id="1"), 'Data de criação': '2026-05-10'}, # Maio
        {**make_ticket(ticket_id="2"), 'Data de criação': '2026-05-22'}, # Maio
        {**make_ticket(ticket_id="3"), 'Data de criação': '2026-04-15'}, # Abril
    ]
    
    df = pd.DataFrame(tickets)

    report = services.campaign_calculator.filter_by_month(df, month=5, year=2026)

    assert len(report) == 2, "Apenas os 2 tickets de Maio devem ser mantidos"

# TESTE 5 - apply_filters (multi-selecao)

def test_apply_filters():
    """
    apply_filters: multi-selecao funciona como AND entre colunas;
    filtro vazio equivale a "todos".
    """

    tickets = [
        make_ticket(ticket_id="1", equipe="Atendimento", prioridade="Urgente"),
        make_ticket(ticket_id="2", equipe="Atendimento", prioridade="Média"),
        make_ticket(ticket_id="3", equipe="Tecnologia", prioridade="Urgente"),
    ]

    df = pd.DataFrame(tickets)

    # multi-selecao: Atendimento AND Urgente -> apenas ticket 1
    filtros = {"Equipes atribuídas": ["Atendimento"], "Prioridade": ["Urgente"]}
    resultado = services.campaign_calculator.apply_filters(df, filtros)
    assert len(resultado) == 1
    assert resultado.iloc[0]["Ticket ID"] == "1"

    # filtro vazio = todos os registros
    vazio = services.campaign_calculator.apply_filters(df, {"Equipes atribuídas": []})
    assert len(vazio) == 3