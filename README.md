# Monitor de Queimadas

Projeto da disciplina Projeto de Bloco: uma solução sustentável alinhada ao ESG e à Agenda 2030, desenvolvida em etapas (TP1: proposta e organização; TP2: interface interativa, scraping e cache; TP3: multipágina, scraping dinâmico e API; TP4: modelos de linguagem locais na API).

O projeto monitora focos de queimadas no Brasil com dados abertos do INPE (Programa Queimadas) e notícias raspadas da Agência Brasil e do G1. Fica no pilar Ambiental do ESG e atende aos ODS 13 (Ação Contra a Mudança Global do Clima) e 15 (Vida Terrestre). A proposta completa está no [Project Charter](docs/project/charter.md) e as fontes de dados no [Data Summary Report](docs/project/data_summary.md).

## Funcionalidades

- Menu de navegação com cinco páginas: Painel, Notícias, Dados, API e Sobre
- Painel com filtros por dia, estado, bioma e FRP, métricas, gráficos e mapa dos focos
- Notícias de duas fontes com nuvem de palavras e estatísticas por fonte e ano
- Upload de CSV complementar (formato INPE) e download dos dados filtrados
- Cache e estado de sessão para manter filtros e uploads entre interações
- Coleta por scripts separados: API do INPE, Beautiful Soup (Agência Brasil) e Selenium (seções do G1, que carregam mais notícias por JavaScript), sempre seguindo o robots.txt de cada site
- API FastAPI com rotas GET e POST sobre os dados, integrada à página API do app
- Análise de sentimento e resumo de textos com modelos do HuggingFace rodando na própria máquina, sem serviços externos

## Estrutura de diretórios (TDSP)

```
monitor-queimadas/
├── README.md
├── requirements.txt
├── requirements-dev.txt        # dependências dos testes
├── pytest.ini
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
│   ├── base_dados.py           # leitura de data/, usada pelo app e pela API
│   ├── api/
│   │   ├── main.py             # API FastAPI: rotas, response models e erros
│   │   └── llm.py              # carga e execução dos modelos de linguagem locais
│   ├── modeling/
│   │   └── avaliar_sentimento.py  # compara abordagens de sentimento num conjunto rotulado
│   └── data_acquisition/
│       ├── fetch_inpe.py       # coleta dos focos via dados abertos do INPE
│       ├── scrape_news.py      # Beautiful Soup na Agência Brasil
│       ├── scrape_news_g1.py   # Selenium nas seções dinâmicas do G1
│       └── robots.py           # respeito ao robots.txt dos sites coletados
├── tests/
│   ├── test_api.py             # testes das rotas e dos códigos de erro
│   ├── test_coleta.py          # testes das funções do scraper do G1
│   ├── test_robots.py          # testes do respeito ao robots.txt
│   └── test_upload.py          # testes da validação de CSVs enviados
└── data/
    ├── raw/                    # CSVs do INPE e das notícias (versionados como fallback)
    └── processed/              # corpus das notícias e conjunto de avaliação do sentimento
```

## CRISP-DM e TDSP

| Fase CRISP-DM | Estágio TDSP | Onde aparece |
|---------------|--------------|--------------|
| Business Understanding | Business Understanding | `docs/project/charter.md` |
| Data Understanding | Data Acquisition & Understanding | `docs/project/data_summary.md`, `code/data_acquisition/`, `data/raw/` |
| Data Preparation | Data Acquisition & Understanding | `data/processed/` (corpus das notícias) |
| Modeling | Modeling | modelos de linguagem locais em `code/api/llm.py`, avaliados em `code/modeling/` |
| Evaluation | Modeling / Acceptance | testes em `tests/` e validação dos KPIs |
| Deployment | Deployment | `app.py` (Streamlit) e `code/api/main.py` (FastAPI) |

## Como executar

Requer Python 3.10 ou superior. Os comandos valem para Linux, macOS e Windows; só a criação e a ativação do ambiente virtual mudam.

No Linux e no macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

No Prompt de Comando (cmd), a ativação é `.venv\Scripts\activate.bat`. Se o PowerShell bloquear o script de ativação, libere-o só para a sessão atual com `Set-ExecutionPolicy -Scope Process RemoteSigned`.

Com o ambiente ativado, o resto é igual em todos os sistemas:

```bash
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

As dependências incluem o PyTorch, então a instalação é grande. Os modelos de linguagem (cerca de 1,4 GB no total) são baixados do HuggingFace na primeira vez que cada análise é usada e ficam em cache na pasta `.cache/huggingface` do usuário.

Para rodar os testes:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Os testes trocam os modelos por respostas fixas e rodam em segundos. Para incluir os modelos reais, ligue a variável `TESTAR_MODELOS`:

```bash
TESTAR_MODELOS=1 python -m pytest
```

```powershell
$env:TESTAR_MODELOS=1; python -m pytest
```

O primeiro comando é para Linux e macOS; o segundo, para o PowerShell do Windows.

## API

A API serve os mesmos dados da aplicação. Para subir, com o ambiente ativado:

```bash
uvicorn code.api.main:app --port 8010
```

A documentação interativa (Swagger) fica em `http://localhost:8010/docs`. Rotas:

| Rota | Função |
|------|--------|
| `GET /saude` | Confirma que a API está no ar, sem ler dados nem modelos |
| `GET /focos?estado=&bioma=&limite=` | Lista focos de calor, com filtros opcionais por estado e bioma e limite de registros. Arquivos novos em `data/raw/` entram sem reiniciar a API |
| `GET /noticias?fonte=` | Lista as notícias raspadas, com filtro opcional por fonte (Agência Brasil ou G1) |
| `POST /focos` | Registra um foco complementar (JSON com lat, lon, estado e opcionalmente município, bioma e FRP); os focos enviados aparecem nas consultas seguintes |
| `POST /processar_texto` | Processa um texto com modelo de linguagem local: `tipo_analise` "sentimento" classifica como positivo, neutro ou negativo; "resumo" gera um resumo em português. A primeira chamada de cada análise baixa o modelo do HuggingFace (fica em cache local) |

Exemplos:

```bash
curl -G http://localhost:8010/focos --data-urlencode "estado=PARÁ" \
  --data-urlencode "bioma=Amazônia" -d limite=5
```

```bash
curl -X POST http://localhost:8010/focos -H "Content-Type: application/json" \
  -d '{"lat": -3.2, "lon": -52.1, "estado": "PARÁ", "bioma": "Amazônia", "frp": 42.5}'
```

```bash
curl -X POST http://localhost:8010/processar_texto -H "Content-Type: application/json" \
  -d '{"texto": "A fumaça das queimadas cobriu a cidade e os atendimentos dispararam.", "tipo_analise": "sentimento"}'
```

As respostas seguem response models (Pydantic). A de `/processar_texto` traz o resultado, o modelo usado, o tempo, o tamanho do texto em tokens e o campo `truncado`, que vale `true` quando o texto passou de 512 tokens (o limite dos modelos) e só o começo foi analisado.

Os erros voltam com código e mensagem explicativa:

| Código | Quando |
|--------|--------|
| 400 | Texto só com espaços |
| 422 | Entrada inválida (texto com menos de 20 caracteres, tipo de análise desconhecido, coordenadas fora do intervalo) |
| 500 | O modelo carregou, mas falhou ao processar o texto |
| 503 | O modelo não pôde ser carregado (dependência faltando ou sem rede no primeiro download), ou os modelos estão ocupados com outros textos há mais de 30 s |
| 504 | O processamento passou de 60 s |

A escolha dos modelos (mDeBERTa multilíngue em classificação zero-shot para sentimento e PTT5 para resumo) está justificada no [Project Charter](docs/project/charter.md), com a avaliação de oito abordagens de sentimento num conjunto rotulado de notícias. Para refazer a comparação: `python -m code.modeling.avaliar_sentimento`.

A página "API" do app usa essas rotas: mostra o status do servidor, consulta focos e notícias, envia um foco pelo formulário e processa textos com o modelo local.
