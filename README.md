<h1 align="center">🐞 Caça aos Bugs - Analyzer</h1>

<p align="center">
  Aplicação web para análise de campanha da <strong> <a href="https://www.zoomeducacaocorporativa.com.br">Zoom Educação Corporativa </a> </strong> <br>
  Processa exports do HubSpot (Excel) e calcula automaticamente a campanha,
  segundo as regras negócio.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-1.50-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="Pandas" src="https://img.shields.io/badge/Pandas-2.3-150458?logo=pandas&logoColor=white">
  <img alt="uv" src="https://img.shields.io/badge/uv-package%20manager-DE5FE9">
</p>

---

## 📖 Sobre

Durante a campanha, os times registram BUGs como tickets no HubSpot, com **prioridade**
e **status**. Cada prioridade vale um valor em reais, e alguns status aplicam penalidade.
Calcular isso manualmente, por colaborador e por mês, é trabalhoso e sujeito a erro.

O **Caça aos Bugs - Analyzer** automatiza essa apuração: você faz upload da planilha
exportada do HubSpot e a aplicação devolve KPIs, um relatório consolidado por colaborador
e um quadro KanBan dos tickets, tudo filtrável por mês, equipe, prioridade e proprietário.

## ✨ Funcionalidades

- **Upload de planilha** `.xlsx` com seleção da aba a analisar
- **Filtros multi-seleção**: Mês, Equipe, Prioridade e Proprietário (vazio = todos)
- **6 KPIs reativos**: Bugs Válidos, HotFix Visão Aluno, HotFix Visão Gestor, BugFix,
  Resolvidos e Aguardando Deploy
- **Relatório consolidado** por colaborador, com saldo em moeda BR (`R$ 1.500,50`) e
  destaque em vermelho para quem tem menos de 5 bugs válidos
- **Kanban visual** dos tickets agrupados por status, com rolagem horizontal e layout
  responsivo (mobile-friendly)
- **Tema Claro/Escuro** nativo do Streamlit, com a identidade visual da Zoom

## 🛠️ Tecnologias

| Camada | Ferramenta |
|---|---|
| Linguagem | Python 3.9+ |
| Gerenciador | [uv](https://docs.astral.sh/uv/) |
| Interface | Streamlit |
| Dados | Pandas + OpenPyXL |
| Testes | Pytest |

## 🚀 Como executar

> Pré-requisito: ter o [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado.

```bash
# clonar o repositório
git clone https://github.com/lucascottetpastor/caca_bugs_analyzer.git
cd caca_bugs_analyzer

# instalar as dependências (cria o ambiente automaticamente)
uv sync

# rodar a aplicação
uv run streamlit run app.py
```

A aplicação abre em `LocalHost`. Para trocar entre tema Claro/Escuro,
use o menu **⋮ → Settings → Theme**.

## 📋 Como usar

1. **Envie a planilha** `.xlsx` exportada do HubSpot.
2. **Escolha a aba** que contém os tickets (geralmente "Todos os Tickets").
3. **Filtre os dados** por mês, equipe, prioridade ou proprietário.
4. Acompanhe os **KPIs**, o **relatório consolidado** e o **Quadro Kanban**. Todos
   recalculam conforme os filtros.

## 📐 Regras de negócio

### Valores por prioridade

| Prioridade | Valor | Categoria |
|---|---|---|
| Urgente | R$ 100,00 | HotFix visão Aluno |
| Alta | R$ 50,00 | HotFix visão Gestor |
| Média | R$ 25,00 | BugFix |
| Baixa | R$ 0,00 |

### Status especiais

- **`Não é bug`**: penalidade de **−R$ 200,00** (exceto se prioridade = Baixa)
- **`Solicitação`**: ignorado, não entra no cálculo de saldo
- **Demais status**: considerados bug válido

### Validações

- Tickets sem **Proprietário** ou sem **Prioridade** são ignorados
- Colunas obrigatórias: `Equipes atribuídas`, `Status do ticket`, `Prioridade`, `Proprietário do ticket`
- Colaboradores precisam de no mínimo **5 bugs válidos** para qualificar na campanha

## 🧪 Testes

```bash
uv run pytest -v
```

A camada de negócio (`services/campaign_calculator.py`) é coberta por testes:
valores por prioridade, penalidade de "Não é bug", filtros multi-seleção,
filtro por mês e contagem de KPIs.
