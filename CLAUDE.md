# Caça aos Bugs — Analyzer

App web para análise da campanha "Caça aos Bugs" da Zoom Educação Corporativa.
Processa exports do HubSpot (Excel) e calcula automaticamente o saldo da campanha
por colaborador segundo regras de prioridade e status.

## Stack

- **Linguagem:** Python 3.12+
- **Gerenciador:** [uv](https://docs.astral.sh/uv/) (NÃO usar pip/venv direto)
- **App:** Streamlit
- **Dados:** Pandas + OpenPyXL
- **Testes:** Pytest
- **Deploy planejado:** Streamlit Community Cloud

## Comandos essenciais

```bash
# rodar o app
uv run streamlit run app.py

# rodar testes
uv run pytest -v

# instalar nova dependência
uv add <nome>

# instalar dep apenas de dev
uv add --dev <nome>
```

## Estrutura

```
caca_bugs_analyzer/
├── app.py                       # entry point Streamlit
├── services/
│   ├── __init__.py
│   └── campaign_calculator.py   # lógica de negócio (camada pura)
├── components/                  # (vazio por enquanto, planejado pra V2)
├── assets/
│   └── style.css
├── tests/
│   ├── test_calculator.py
│   └── fixtures/
│       └── cacabugs_maio.xlsx   # dado real, NÃO versionado
├── .streamlit/
│   └── config.toml              # tema customizado (roxo/grafite/ciano)
├── docs/
│   └── V2_PLAN.md               # plano da V2
├── pyproject.toml
└── uv.lock
```

## Padrão de assistência (como Claude deve atuar)

**Padrão "planeja → executa → confirma":**

1. Antes de codar qualquer mudança não-trivial, gerar um **plano curto** (3–5 bullets) descrevendo o que vai mudar e em quais arquivos.
2. Lucas confirma ou ajusta o plano.
3. Claude executa as mudanças.
4. Após cada execução, Claude mostra o que mudou e pergunta como prosseguir.

**NUNCA** fazer mais de uma etapa do plano sem confirmação.

**SEMPRE** rodar `uv run pytest -v` antes de propor commit. Commit com teste vermelho é proibido.

**SEMPRE** propor mensagens de commit no padrão Conventional Commits:
- `feat:` nova funcionalidade visível ao usuário
- `fix:` correção de bug
- `refactor:` mudança sem alterar comportamento
- `test:` adicionar ou ajustar testes
- `chore:` configuração, build, deps

## Padrões de código do Lucas

- **Docstrings**: estilo simples com `Args:` e `Returns:`, usando `->` antes de cada item dos returns
- **Comentários**: curtos, em minúsculas, sem acentos quando possível (`# garantia que todas colunas existem!`)
- **Strings**: aspas duplas como padrão
- **Agregações pandas**: usar `pd.NamedAgg(column=..., aggfunc=...)` em vez da forma de tupla
- **Pequenas funções com responsabilidade única**: nada de funções enormes; preferir várias pequenas
- **Nomes em português** quando se referem a regras de negócio (Proprietário, Prioridade, etc.)
- **Constantes em UPPER_SNAKE_CASE** no topo do arquivo, com comentário explicando

## Regras de negócio (Campanha Caça aos Bugs)

### Valores por prioridade (tickets considerados bug)

| Prioridade | Valor |
|---|---|
| Urgente | R$ 100,00 |
| Alta | R$ 50,00 |
| Média | R$ 25,00 |
| Baixa | R$ 0,00 (não conta em `total_bugs`, vai pra `bugs_baixa`) |

### Status especiais

- **`Não é bug`**:
  - Se prioridade ≠ Baixa → penalidade de **−R$ 200,00**
  - Se prioridade = Baixa → R$ 0 (sem penalidade)
- **`Solicitação`** → ignorado, não entra no relatório
- **Demais status** (em Back-end, Deploy resolvido, em Teste, em Front-end, Aguardando deploy, Backlog de melhorias, Bug detectado, etc.) → consideradas como bug válido

### Validações

- Tickets sem `Proprietário do ticket` ou sem `Prioridade` → **ignorados** (regra aplicada em `remove_invalid_tickets`)
- Colunas obrigatórias na planilha: `Equipes atribuídas`, `Status do ticket`, `Prioridade`, `Proprietário do ticket`
- Validação central em `validate_columns()` que levanta `ValueError` com mensagem amigável

### Decisões arquiteturais já tomadas

1. **Strings de UI** virão de `locales/pt_BR.json` (i18n preparado, mas não implementado ainda)
2. **Aba da planilha**: usuário escolhe via dropdown (não assumir nome fixo)
3. **Linha 1 da aba** = header (nomes das colunas)
4. **Planilha real** (`cacabugs_maio.xlsx`) NÃO é versionada (LGPD). Antes do deploy, criar `campanha_sample.xlsx` anonimizada
5. **Filtro de equipe** removido do `calculate_report` na V2 — agora é responsabilidade da UI (filtro multi-seleção)
6. **`calculate_report` recebe DataFrame já filtrado** — não chama mais filtros internamente

## Funções do `services/campaign_calculator.py`

| Função | Responsabilidade |
|---|---|
| `list_sheet_names(file)` | Lista abas da planilha Excel |
| `read_sheet(file, sheet_name)` | Lê uma aba específica (header na linha 1) |
| `validate_columns(df)` | Valida colunas obrigatórias, raise ValueError se faltar |
| `filter_teams(df)` | Filtra só time de Atendimento (mantida pra uso pontual, não usada no fluxo principal V2) |
| `remove_invalid_tickets(df)` | Remove tickets sem proprietário/prioridade |
| `filter_by_month(df, year, month)` | Filtra por mês de criação |
| `get_available_months(df)` | Lista (ano, mês) presentes na planilha |
| `apply_filters(df, filters)` | (V2) Aplica filtros multi-seleção genéricos |
| `calculate_ticket_value(row)` | Calcula valor de 1 ticket |
| `calculate_report(df)` | Gera relatório consolidado por colaborador |

## Constantes do `campaign_calculator.py`

```python
PRIORITY_VALUES = {
    "Urgente": 100.0,
    "Alta": 50.0,
    "Média": 25.0,
    "Baixa": 0.0,
}
NOT_A_BUG_STATUS = "Não é bug"
NOT_A_BUG_PENALTY = -200.0
ELIGIBLE_TEAM = "Atendimento"
IGNORED_STATUSES = ["Solicitação"]
INFORMATIVE_PRIORITY = "Baixa"
REQUIRED_COLUMNS = [
    "Equipes atribuídas",
    "Status do ticket",
    "Prioridade",
    "Proprietário do ticket",
]
```

## Tema visual (paleta)

Definida em `.streamlit/config.toml`:

```toml
[theme]
base = "dark"
primaryColor = "#7C3AED"            # roxo vibrante
backgroundColor = "#0F172A"         # grafite escuro
secondaryBackgroundColor = "#1E293B"
textColor = "#F1F5F9"
font = "sans serif"
```

Para badges/tags de prioridade no Kanban (V2):
- Urgente → vermelho coral (#EF4444)
- Alta → âmbar (#F59E0B)
- Média → roxo primário (#7C3AED)
- Baixa → ciano accent (#06B6D4)

## Idioma

Toda comunicação com o Lucas é em **português brasileiro**. Docstrings, comentários
e mensagens de erro também em português.
