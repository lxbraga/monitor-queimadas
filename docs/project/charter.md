# Project Charter: Monitor de Queimadas

Artefato da fase de Business Understanding do TDSP, sob responsabilidade do Project Manager.

## Contexto e problema de negócio

As queimadas destroem vegetação nativa, ameaçam a biodiversidade, pioram a qualidade do ar e respondem por boa parte das emissões brasileiras de gases de efeito estufa. O INPE detecta dezenas de milhares de focos de calor por dia via satélite, mas publica esses dados em arquivos técnicos que pouca gente consegue aproveitar.

O problema que o projeto ataca: gestores públicos, ONGs e a sociedade civil não têm uma visão consolidada e atualizada dos focos de queimadas no Brasil, o que dificulta priorizar prevenção, fiscalização e resposta.

A solução proposta é um painel que coleta automaticamente os focos detectados pelo INPE e os organiza por estado, município e bioma, em linguagem acessível.

## Escopo por etapa

TP1 (concluído):

- Proposta e planejamento do projeto (este documento).
- Diretórios organizados segundo o ciclo de vida do TDSP.
- Primeiro esboço do Data Summary Report ([data_summary.md](data_summary.md)).
- Coleta de dados via API de dados abertos do INPE (`code/data_acquisition/fetch_inpe.py`).
- Demo em Streamlit com amostra dos dados.

TP2 (concluído):

- Interface interativa com abas, filtros por dia, estado, bioma e FRP, métricas, gráficos e mapa.
- Scraping de notícias da Agência Brasil com Beautiful Soup (`code/data_acquisition/scrape_news.py`), executado como script separado, alimentando tabela de notícias, nuvem de palavras e estatísticas no app.
- Cache (`st.cache_data`) e estado de sessão (`st.session_state`) para performance e persistência dos filtros e uploads.
- Upload de CSV complementar e download dos dados filtrados.
- Repositório no GitHub e preparação para deploy no Streamlit Community Cloud.

TP3 (concluído):

- Aplicação reorganizada em múltiplas páginas com menu de navegação (Painel, Notícias, Dados, API e Sobre).
- Scraping de página dinâmica com Selenium na busca do G1, que carrega os resultados por JavaScript (`code/data_acquisition/scrape_news_g1.py`), somando uma segunda fonte de notícias ao corpus.
- API em FastAPI (`code/api/main.py`) com consulta de focos e notícias (GET) e registro de focos complementares (POST), documentada no Swagger em `/docs` e integrada ao app pela página API.
- Metas reavaliadas: além do painel, o projeto passa a oferecer acesso programático aos dados, o que abre caminho para integrações externas e para os LLMs da próxima etapa.

TP4 (concluído):

- Modelos de linguagem locais integrados à API: análise de sentimento e resumo automático, rodando na própria máquina via HuggingFace Transformers, sem serviços externos.
- Rota `POST /processar_texto` com response models (Pydantic) e respostas estruturadas; as rotas existentes também ganharam response models.
- Tratamento robusto de erros: 422 para entrada inválida, 400 para texto vazio e 503 com mensagem explicativa quando o modelo não pode ser carregado.
- Justificativa da escolha dos modelos documentada abaixo.
- Seção "Processar texto" na página API do app, consumindo a nova rota.

Fica para a entrega final: ampliar os usos de LLM sobre o corpus (Q&A e geração de relatórios) e refinar a aplicação para apresentação.

## Objetivos

1. Reunir os dados oficiais de focos de queimadas em um só lugar, com coleta automática.
2. Mostrar rapidamente quais estados, municípios e biomas concentram mais focos.
3. Apoiar decisões de prevenção e resposta com indicadores objetivos.
4. Aproximar o público geral dos dados oficiais.

## Metas e indicadores de sucesso

| Meta | Indicador | Alvo |
|------|-----------|------|
| Coleta automatizada | Pipeline baixa o CSV diário do INPE sem intervenção manual | 100% automático, tolerando atraso de publicação de até 5 dias |
| Aplicação reprodutível | App roda a partir do `requirements.txt` em ambiente limpo | Instalação e execução sem erros |
| Cobertura dos dados | Focos de todo o Brasil com localização, bioma, risco de fogo e FRP | Arquivo diário completo |
| Utilidade analítica | Focos por estado e bioma, FRP médio e mapa no dashboard, com filtros | Entregue no TP2 |
| Contexto jornalístico | Notícias raspadas exibidas com nuvem de palavras e estatísticas | Entregue no TP2, ampliado no TP3 com o G1 |
| Acesso programático | Rotas GET e POST servindo focos e notícias em JSON | Entregue no TP3 |
| Adoção (etapas futuras) | Feedback de usuários do público-alvo | Avaliação positiva na entrega final |

## ODS atendidos

O projeto fica no pilar Ambiental do ESG e atende a dois ODS da Agenda 2030:

- **ODS 13 (Ação Contra a Mudança Global do Clima):** queimadas estão entre as maiores fontes de emissão de CO₂ do país. Tornar o monitoramento acessível fortalece a resposta e a conscientização (metas 13.1 e 13.3).
- **ODS 15 (Vida Terrestre):** os focos atingem diretamente os biomas brasileiros e sua biodiversidade. O painel evidencia quais biomas estão sob maior pressão (metas 15.1 e 15.2).

## Público-alvo

- Gestores públicos ambientais: priorização de fiscalização e brigadas.
- ONGs e sociedade civil: planejamento de campanhas e ações de conservação.
- Jornalistas: reportagens baseadas em dados oficiais.
- Pesquisadores e estudantes: dados já organizados.
- Cidadãos: situação das queimadas na sua região.

## Stakeholders

| Stakeholder | Papel |
|-------------|-------|
| Aluno (Lucas Braga) | Executa os papéis TDSP: Project Lead, Project Manager, Data Scientist e Solution Architect |
| Professor da disciplina | Sponsor: define requisitos e avalia as entregas |
| INPE (Programa Queimadas) | Provedor dos dados abertos |
| Público-alvo | Usuários finais |

## Metodologia: CRISP-DM e TDSP

| Fase CRISP-DM | Estágio TDSP | Neste projeto |
|---------------|--------------|---------------|
| Business Understanding | Business Understanding | Project Charter (este documento) |
| Data Understanding | Data Acquisition & Understanding | Data Summary Report, `fetch_inpe.py`, `scrape_news.py`, `scrape_news_g1.py`, dados em `data/raw/` |
| Data Preparation | Data Acquisition & Understanding | Corpus das notícias em `data/processed/`, agregações no app |
| Modeling | Modeling | Análises e integração com LLMs (próximas etapas) |
| Evaluation | Modeling / Acceptance | Validação dos indicadores contra as metas (próximas etapas) |
| Deployment | Deployment | Dashboard em `app.py`, pronto para o Streamlit Community Cloud |

No diagrama TDSP do enunciado, o Project Charter é artefato do estágio de Business Understanding e o Data Summary Report do estágio de Data Ingest & Understanding. Por isso os dois ficam em `docs/project/`.

## Arquitetura

Coleta em scripts separados: `requests` para os CSVs do INPE, Beautiful Soup para as notícias da Agência Brasil e Selenium para a busca dinâmica do G1, gravando em `data/raw/` e `data/processed/`. Tratamento com `pandas`. Duas portas de acesso aos dados: a aplicação Streamlit multipágina (com cache e estado de sessão) e a API FastAPI com rotas GET e POST. A API também executa os modelos de linguagem locais (HuggingFace Transformers com PyTorch) para sentimento e resumo, carregados sob demanda em `code/api/llm.py`.

## Escolha dos modelos LLM

Critérios usados: desempenho na tarefa em português, custo computacional para rodar localmente (CPU de um notebook, sem GPU dedicada) e acessibilidade (download aberto pelo HuggingFace, carregável com a biblioteca Transformers). Dois modelos atendem às duas análises do projeto:

| Tarefa | Modelo | Por que ele |
|--------|--------|-------------|
| Sentimento | `lxyuan/distilbert-base-multilingual-cased-sentiments-student` | DistilBERT multilíngue destilado para sentimento, com bom desempenho em português; ~540 MB, classifica em menos de 0,1 s em CPU; download aberto no HuggingFace |
| Resumo | `recogna-nlp/ptt5-base-summ` | PTT5 (T5 pré-treinado em português pelo grupo Recogna/Unesp) ajustado para sumarização de notícias, exatamente o domínio do corpus; ~1,2 GB, resume em 1 a 3 s em CPU |

Alternativas consideradas: modelos generativos maiores (como os da família Llama) dariam respostas mais flexíveis, mas pedem vários GB de memória e latência alta sem GPU; BERT puro exigiria ajuste fino próprio. Os dois escolhidos são especializados, leves e prontos para uso.

Limitações conhecidas: o classificador de sentimento é multilíngue, não especializado em português, e textos ambíguos ficam com confiança baixa; o resumidor funciona melhor com textos de notícia completos e pode gerar prefixos estranhos em textos muito curtos ou genéricos.

Os modelos são baixados na primeira chamada e ficam no cache local do HuggingFace; depois disso a API funciona sem rede. O carregamento é preguiçoso (na primeira requisição de cada análise) para a API subir rápido.

## Preparação para LLMs

Os dados coletados já estão em formatos prontos para as tarefas com LLMs da próxima etapa:

| Caso de uso | Dado de entrada | Situação |
|-------------|-----------------|----------|
| Resumo automático de notícias | Texto completo dos artigos em `data/processed/corpus_noticias.txt` e `corpus_g1.txt` | Entregue no TP4 via `POST /processar_texto` |
| Classificação de sentimento | Títulos e textos das notícias das duas fontes | Entregue no TP4 via `POST /processar_texto` |
| Perguntas e respostas (Q&A) | Corpus de notícias e estatísticas dos focos | Entrega final |
| Geração de relatórios | Agregados de focos por estado, bioma e dia | Entrega final |

A API facilita a integração: o serviço de LLM poderá consultar focos e notícias pelas mesmas rotas usadas pela interface.

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Servidor do INPE fora do ar | App sem dados atualizados | Amostra local versionada em `data/raw/`; coleta recua até 5 dias |
| Mudança no formato ou URL dos arquivos | Quebra da coleta | Coleta isolada em `fetch_inpe.py`; fontes alternativas mapeadas no Data Summary Report |
| Sazonalidade (poucos focos na estação chuvosa) | Painel pouco expressivo em certos meses | Usar agregados mensais e históricos nas próximas etapas |
| Mudança no HTML da Agência Brasil ou do G1 | Quebra do scraping | Scrapers isolados em scripts próprios; dados raspados versionados como fallback |
| Busca do G1 mistura a cidade de Queimadas (BA/PB) | Corpus contaminado com assunto fora do tema | Scraper descarta URLs de eleições e links fora do padrão de notícia |
