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

# TESTE 6 - calculate_kpis (contagem por prioridade e por status)

def test_calculate_kpis():
    """
    calculate_kpis conta bugs validos por prioridade
    (Urgente=HotFix Aluno, Alta=HotFix Gestor, Média=BugFix)
    e tickets por status de workflow (Deploy (resolvido), Aguardando deploy).
    """

    tickets = [
        make_ticket(ticket_id="1", prioridade="Urgente"),
        make_ticket(ticket_id="2", prioridade="Urgente", status="Deploy (resolvido)"),
        make_ticket(ticket_id="3", prioridade="Alta", status="Aguardando deploy"),
        make_ticket(ticket_id="4", prioridade="Média"),
        make_ticket(ticket_id="5", prioridade="Baixa"),
        # "Não é bug" nao conta como bug valido
        make_ticket(ticket_id="6", prioridade="Urgente", status="Não é bug"),
        # melhoria = Baixa + Tipo Bug "Melhoria"
        {**make_ticket(ticket_id="7", prioridade="Baixa"), "Tipo Bug": "Melhoria"},
    ]

    df = pd.DataFrame(tickets)

    kpis = services.campaign_calculator.calculate_kpis(df)

    assert kpis["hotfix_aluno"] == 2
    assert kpis["hotfix_gestor"] == 1
    assert kpis["bugfix"] == 1
    assert kpis["bugs_validos"] == 4
    assert kpis["melhoria"] == 1
    assert kpis["resolvidos"] == 1

# TESTE 7 - classificacao de melhoria (Baixa + Tipo Bug = Melhoria)

def test_classificacao_melhoria():
    """
    melhoria exige as duas condicoes: Prioridade Baixa E Tipo Bug "Melhoria".
    Baixa sem o tipo conta so em baixa_prioridade; o tipo Melhoria fora de Baixa
    nao conta. A comparacao do tipo ignora maiuscula/minuscula e espacos.
    """

    tickets = [
        # melhoria de verdade -> conta em melhoria E baixa_prioridade
        {**make_ticket(ticket_id="1", prioridade="Baixa"), "Tipo Bug": "Melhoria"},
        # match flexivel: espacos e caixa diferente ainda casam
        {**make_ticket(ticket_id="2", prioridade="Baixa"), "Tipo Bug": "  melhoria "},
        # Baixa sem tipo melhoria -> so baixa_prioridade
        {**make_ticket(ticket_id="3", prioridade="Baixa"), "Tipo Bug": "Bug-fix"},
        # tipo Melhoria fora de Baixa -> nao conta como melhoria
        {**make_ticket(ticket_id="4", prioridade="Urgente"), "Tipo Bug": "Melhoria"},
    ]

    df = pd.DataFrame(tickets)

    report = services.campaign_calculator.calculate_report(df)

    row = report.iloc[0]
    assert row["total_cards"] == 4
    assert row["baixa_prioridade"] == 3   # tickets 1, 2 e 3 sao Baixa
    assert row["melhoria"] == 2           # apenas tickets 1 e 2
    assert row["bugs_validos"] == 1       # ticket 4 (Urgente) ainda e bug valido

# TESTE 8 - sem a coluna Tipo Bug, melhoria fica zerada

def test_melhoria_sem_coluna_tipo_bug():
    """
    Exports antigos nao tem a coluna "Tipo Bug"; o relatorio deve rodar normal
    e a contagem de melhoria deve ser 0.
    """

    tickets = [
        make_ticket(ticket_id="1", prioridade="Baixa"),
        make_ticket(ticket_id="2", prioridade="Média"),
    ]

    df = pd.DataFrame(tickets)

    report = services.campaign_calculator.calculate_report(df)

    row = report.iloc[0]
    assert row["baixa_prioridade"] == 1
    assert row["melhoria"] == 0

# TESTE 9 - classify_bug_type (categorias do filtro)

def test_classify_bug_type():
    """
    classify_bug_type mapeia o valor cru de Tipo Bug nas 5 categorias canonicas.
    Match por substring (caixa/espacos ignorados); vazio -> "Não Considerado BUG".
    """

    tickets = [
        {**make_ticket(ticket_id="1"), "Tipo Bug": "Hot-fix visão aluno (impede o aluno de estudar)"},
        {**make_ticket(ticket_id="2"), "Tipo Bug": "Hot-fix visão gestor (impede criar/editar trilhas)"},
        {**make_ticket(ticket_id="3"), "Tipo Bug": "Bug-fix (não impede estudar/gestão do aprendizado)"},
        {**make_ticket(ticket_id="4"), "Tipo Bug": "  MELHORIA "},  # match flexivel
        {**make_ticket(ticket_id="5"), "Tipo Bug": None},           # vazio
    ]

    df = pd.DataFrame(tickets)

    categorias = services.campaign_calculator.classify_bug_type(df).tolist()

    assert categorias == [
        "HotFix Visão Aluno",
        "HotFix Visão Gestor",
        "BugFix",
        "Melhoria",
        "Não Considerado BUG",
    ]

# TESTE 10 - classify_bug_type sem a coluna Tipo Bug

def test_classify_bug_type_sem_coluna():
    """
    Sem a coluna "Tipo Bug" (exports antigos), tudo vira "Não Considerado BUG".
    """

    df = pd.DataFrame([make_ticket(ticket_id="1"), make_ticket(ticket_id="2")])

    categorias = services.campaign_calculator.classify_bug_type(df).tolist()

    assert categorias == ["Não Considerado BUG", "Não Considerado BUG"]