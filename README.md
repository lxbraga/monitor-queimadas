# Monitor de Queimadas

TP1 da disciplina IA Aplicada (Infnet): proposta, planejamento e organização de uma solução sustentável alinhada ao ESG e à Agenda 2030.

O projeto monitora focos de queimadas no Brasil com dados abertos do INPE (Programa Queimadas), coletados via API. Fica no pilar Ambiental do ESG e atende aos ODS 13 (Ação Contra a Mudança Global do Clima) e 15 (Vida Terrestre). A proposta completa está no [Project Charter](docs/project/charter.md) e as fontes de dados no [Data Summary Report](docs/project/data_summary.md).

## Estrutura de diretórios (TDSP)

```
entrega/
├── README.md
├── requirements.txt            # dependências, na raiz da entrega
├── app.py                      # demo Streamlit
├── docs/
│   └── project/                # artefatos de gestão (TDSP)
│       ├── charter.md          # Project Charter (Business Understanding)
│       └── data_summary.md     # Data Summary Report (Data Acquisition & Understanding)
├── code/
│   └── data_acquisition/
│       └── fetch_inpe.py       # coleta dos focos via dados abertos do INPE
└── data/
    ├── raw/                    # dados brutos (amostra versionada como fallback)
    └── processed/              # dados tratados (próximas fases)
```

## CRISP-DM e TDSP

| Fase CRISP-DM | Estágio TDSP | Onde aparece |
|---------------|--------------|--------------|
| Business Understanding | Business Understanding | `docs/project/charter.md` |
| Data Understanding | Data Acquisition & Understanding | `docs/project/data_summary.md`, `code/data_acquisition/`, `data/raw/` |
| Data Preparation | Data Acquisition & Understanding | `data/processed/` (próximas etapas) |
| Modeling | Modeling | análises e LLMs (próximas etapas) |
| Evaluation | Modeling / Acceptance | validação dos KPIs (próximas etapas) |
| Deployment | Deployment | `app.py`, depois o dashboard final |

## Como executar

Requer Python 3.10 ou superior.

```bash
# criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# instalar as dependências
pip install -r requirements.txt

# (opcional) coletar os dados mais recentes do INPE
python code/data_acquisition/fetch_inpe.py

# rodar a demo
streamlit run app.py
```

O app abre em `http://localhost:8501` com o título do projeto, a descrição do problema e dos objetivos, links úteis e uma tabela com amostra dos dados do INPE, com botão para atualizá-los via API.
