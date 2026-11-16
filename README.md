# Monitor de Queimadas

Projeto da disciplina Projeto de Bloco: uma solução sustentável alinhada ao ESG e à Agenda 2030, desenvolvida em etapas (TP1: proposta e organização; TP2: interface interativa, scraping e cache; TP3: multipágina, scraping dinâmico e API).

O projeto monitora focos de queimadas no Brasil com dados abertos do INPE (Programa Queimadas) e notícias raspadas da Agência Brasil e do G1. Fica no pilar Ambiental do ESG e atende aos ODS 13 (Ação Contra a Mudança Global do Clima) e 15 (Vida Terrestre). A proposta completa está no [Project Charter](docs/project/charter.md) e as fontes de dados no [Data Summary Report](docs/project/data_summary.md).

## Funcionalidades

- Menu de navegação com cinco páginas: Painel, Notícias, Dados, API e Sobre
- Painel com filtros por dia, estado, bioma e FRP, métricas, gráficos e mapa dos focos
- Notícias de duas fontes com nuvem de palavras e estatísticas por fonte e ano
- Upload de CSV complementar (formato INPE) e download dos dados filtrados
- Cache e estado de sessão para manter filtros e uploads entre interações
- Coleta por scripts separados: API do INPE, Beautiful Soup (Agência Brasil) e Selenium (G1, cuja busca carrega os resultados por JavaScript)
- API FastAPI com rotas GET e POST sobre os dados, integrada à página API do app

## Estrutura de diretórios (TDSP)

```
monitor-queimadas/
├── README.md
├── requirements.txt
├── app.py                      # entrada do app: menu de navegação
├── views/                      # uma página por funcionalidade
│   ├── painel.py               # filtros, métricas, gráficos e mapa
│   ├── noticias.py             # nuvem de palavras e tabela de notícias
│   ├── dados.py                # amostra, upload e download de CSV
│   ├── consulta_api.py         # integração com a API FastAPI
│   └── sobre.py                # problema, objetivos, ODS e links
├── docs/
│   └── project/                # artefatos de gestão (TDSP)
│       ├── charter.md          # Project Charter (Business Understanding)
│       └── data_summary.md     # Data Summary Report (Data Acquisition & Understanding)
├── code/
│   ├── app_utils.py            # funções compartilhadas pelas páginas
│   ├── api/
│   │   └── main.py             # API FastAPI (GET e POST)
│   └── data_acquisition/
│       ├── fetch_inpe.py       # coleta dos focos via dados abertos do INPE
│       ├── scrape_news.py      # Beautiful Soup na Agência Brasil
│       └── scrape_news_g1.py   # Selenium na busca dinâmica do G1
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

# (opcional) raspar as notícias do G1 com Selenium (requer Chrome instalado)
python code/data_acquisition/scrape_news_g1.py

# rodar a aplicação
streamlit run app.py
```

Os scripts de coleta são opcionais porque o repositório já traz dados em `data/` como fallback. Na interface, o botão "Atualizar dados do INPE" baixa os dias mais recentes sem sair do app.

## API

A API serve os mesmos dados da aplicação. Para subir:

```bash
.venv/bin/uvicorn code.api.main:app --port 8010
```

A documentação interativa (Swagger) fica em `http://localhost:8010/docs`. Rotas:

| Rota | Função |
|------|--------|
| `GET /focos?estado=&bioma=&limite=` | Lista focos de calor, com filtros opcionais por estado e bioma e limite de registros |
| `GET /noticias?fonte=` | Lista as notícias raspadas, com filtro opcional por fonte (Agência Brasil ou G1) |
| `POST /focos` | Registra um foco complementar (JSON com lat, lon, estado e opcionalmente município, bioma e FRP); os focos enviados aparecem nas consultas seguintes |
| `POST /processar_texto` | Processa um texto com modelo de linguagem local: `tipo_analise` "sentimento" classifica como positivo, neutro ou negativo; "resumo" gera um resumo em português. A primeira chamada de cada análise baixa o modelo do HuggingFace (fica em cache local) |

Exemplos:

```bash
curl "http://localhost:8010/focos?estado=PARÁ&bioma=Amazônia&limite=5"
```

```bash
curl -X POST http://localhost:8010/focos -H "Content-Type: application/json" \
  -d '{"lat": -3.2, "lon": -52.1, "estado": "PARÁ", "bioma": "Amazônia", "frp": 42.5}'
```

```bash
curl -X POST http://localhost:8010/processar_texto -H "Content-Type: application/json" \
  -d '{"texto": "A fumaça das queimadas cobriu a cidade e os atendimentos dispararam.", "tipo_analise": "sentimento"}'
```

As respostas seguem response models (Pydantic) e os erros voltam com códigos e mensagens claras: 422 para entrada inválida, 400 para texto vazio e 503 quando o modelo não pode ser carregado. A escolha dos modelos (DistilBERT multilíngue para sentimento e PTT5 para resumo) está justificada no [Project Charter](docs/project/charter.md).

A página "API" do app usa essas rotas: mostra o status do servidor, consulta focos e notícias, envia um foco pelo formulário e processa textos com o modelo local.
