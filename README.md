# Monitor de Queimadas

Projeto da disciplina Projeto de Bloco: uma solução sustentável alinhada ao ESG e à Agenda 2030, desenvolvida em etapas (TP1: proposta e organização; TP2: interface interativa, scraping e cache).

O projeto monitora focos de queimadas no Brasil com dados abertos do INPE (Programa Queimadas) e notícias raspadas da Agência Brasil. Fica no pilar Ambiental do ESG e atende aos ODS 13 (Ação Contra a Mudança Global do Clima) e 15 (Vida Terrestre). A proposta completa está no [Project Charter](docs/project/charter.md) e as fontes de dados no [Data Summary Report](docs/project/data_summary.md).

## Funcionalidades

- Painel com filtros por dia, estado, bioma e FRP, métricas, gráficos e mapa dos focos
- Notícias sobre queimadas com nuvem de palavras e estatísticas por categoria e ano
- Upload de CSV complementar (formato INPE) e download dos dados filtrados
- Cache e estado de sessão para manter filtros e uploads entre interações
- Coleta de dados por scripts separados: API do INPE e scraping com Beautiful Soup

## Estrutura de diretórios (TDSP)

```
monitor-queimadas/
├── README.md
├── requirements.txt
├── app.py                      # aplicação Streamlit
├── docs/
│   └── project/                # artefatos de gestão (TDSP)
│       ├── charter.md          # Project Charter (Business Understanding)
│       └── data_summary.md     # Data Summary Report (Data Acquisition & Understanding)
├── code/
│   └── data_acquisition/
│       ├── fetch_inpe.py       # coleta dos focos via dados abertos do INPE
│       └── scrape_news.py      # scraping de notícias da Agência Brasil
└── data/
    ├── raw/                    # CSVs do INPE e das notícias (versionados como fallback)
    └── processed/              # corpus de texto das notícias
```

## CRISP-DM e TDSP

| Fase CRISP-DM | Estágio TDSP | Onde aparece |
|---------------|--------------|--------------|
| Business Understanding | Business Understanding | `docs/project/charter.md` |
| Data Understanding | Data Acquisition & Understanding | `docs/project/data_summary.md`, `code/data_acquisition/`, `data/raw/` |
| Data Preparation | Data Acquisition & Understanding | `data/processed/` (corpus das notícias) |
| Modeling | Modeling | análises e LLMs (próximas etapas) |
| Evaluation | Modeling / Acceptance | validação dos KPIs (próximas etapas) |
| Deployment | Deployment | `app.py` e deploy no Streamlit Community Cloud |

## Como executar

Requer Python 3.10 ou superior.

```bash
# criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# instalar as dependências
pip install -r requirements.txt

# (opcional) coletar os últimos 3 dias de focos do INPE
python code/data_acquisition/fetch_inpe.py 3

# (opcional) raspar as notícias da Agência Brasil
python code/data_acquisition/scrape_news.py

# rodar a aplicação
streamlit run app.py
```

Os scripts de coleta são opcionais porque o repositório já traz dados em `data/` como fallback. Na interface, o botão "Atualizar dados do INPE" baixa os dias mais recentes sem sair do app.
