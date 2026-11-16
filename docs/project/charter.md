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
- Tratamento robusto de erros, com mensagem explicativa em cada caso: 400 para texto vazio, 422 para entrada inválida, 500 para falha no processamento, 503 quando o modelo não pode ser carregado e 504 quando o processamento passa de 60 s.
- A resposta avisa (campo `truncado`) quando o texto passa do limite de 512 tokens dos modelos.
- Testes automatizados das rotas e dos códigos de erro em `tests/`.
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
| Análise de texto local | Sentimento e resumo de notícias sem serviços externos, com erros tratados | Entregue no TP4 |
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
| Modeling | Modeling | Modelos de linguagem locais para sentimento e resumo (`code/api/llm.py`), com a avaliação do sentimento em `code/modeling/avaliar_sentimento.py` |
| Evaluation | Modeling / Acceptance | Testes automatizados em `tests/`; validação dos indicadores contra as metas na entrega final |
| Deployment | Deployment | Dashboard em `app.py` e API em `code/api/main.py`, executados localmente |

No diagrama TDSP do enunciado, o Project Charter é artefato do estágio de Business Understanding e o Data Summary Report do estágio de Data Ingest & Understanding. Por isso os dois ficam em `docs/project/`.

## Arquitetura

Coleta em scripts separados: `requests` para os CSVs do INPE, Beautiful Soup para as notícias da Agência Brasil e Selenium para a busca dinâmica do G1, gravando em `data/raw/` e `data/processed/`. Tratamento com `pandas`. Duas portas de acesso aos dados: a aplicação Streamlit multipágina (com cache e estado de sessão) e a API FastAPI com rotas GET e POST. A API também executa os modelos de linguagem locais (HuggingFace Transformers com PyTorch) para sentimento e resumo, carregados sob demanda em `code/api/llm.py`.

## Escolha dos modelos LLM

Critérios usados: desempenho na tarefa em português, custo computacional para rodar localmente (CPU de um notebook, sem GPU dedicada) e acessibilidade (download aberto pelo HuggingFace, carregável com a biblioteca Transformers). Dois modelos atendem às duas análises do projeto:

| Tarefa | Modelo | Por que ele |
|--------|--------|-------------|
| Sentimento | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, em classificação zero-shot | Modelo de inferência textual treinado em mais de 100 idiomas, incluindo português. Em vez de um classificador de sentimento pronto, ele julga qual hipótese o texto confirma: "Esta notícia é positiva", "negativa" ou "neutra". Foi a abordagem que melhor entendeu notícias sobre queimadas na avaliação abaixo; ~530 MB, cerca de 90 ms por texto em CPU |
| Resumo | `recogna-nlp/ptt5-base-summ` | PTT5 (T5 pré-treinado em português pelo grupo Recogna/Unesp) ajustado para sumarização de notícias, exatamente o domínio do corpus; ~890 MB, resume em 1 a 5 s em CPU |

### Avaliação do sentimento

O primeiro modelo escolhido, um classificador de sentimento multilíngue (DistilBERT), errava notícias boas sobre queimadas: palavras como "incêndio", "fumaça" e "focos" puxavam o resultado para negativo, e quase todo texto do projeto tem essas palavras. Para escolher com dados, montamos um conjunto rotulado em `data/processed/avaliacao_sentimento.csv`, com 54 textos (20 negativos, 20 positivos e 14 neutros): 33 títulos reais das notícias raspadas e 21 frases escritas no mesmo estilo, positivas e neutras, com vocabulário de fogo. Os rótulos foram atribuídos manualmente e só entraram casos sem ambiguidade.

| Abordagem | Acerto | F1 macro | Positivos | Neutros | Negativos | ms por texto |
|-----------|--------|----------|-----------|---------|-----------|--------------|
| **Zero-shot mDeBERTa, hipótese "Esta notícia é {}." (em uso)** | **70%** | **0,58** | **85%** | 7% | **100%** | 91 |
| Classificador XLM-R (`cardiffnlp/twitter-xlm-roberta-base-sentiment`) | 52% | 0,48 | 15% | 86% | 65% | 42 |
| Zero-shot mDeBERTa, hipótese "Esta é uma notícia {}." | 52% | 0,48 | 50% | 14% | 80% | 53 |
| LLM Qwen2.5 0,5B com instrução | 52% | 0,39 | 100% | 0% | 40% | 181 |
| LLM Qwen2.5 1,5B com instrução | 48% | 0,35 | 30% | 0% | 100% | 376 |
| Classificador DistilBERT (`lxyuan/...-sentiments-student`, escolha anterior) | 37% | 0,28 | 30% | 0% | 70% | 25 |
| Classificador BERTweet-pt (`pysentimiento/bertweet-pt-sentiment`) | 35% | 0,28 | 0% | 100% | 25% | 25 |
| Classificador DistilBERT multilíngue (`tabularisai/multilingual-sentiment-analysis`) | 30% | 0,20 | 0% | 100% | 10% | 24 |

Os classificadores prontos foram treinados com tweets e avaliações de produtos, onde vocabulário de fogo quase sempre indica algo ruim; os LLMs pequenos não seguiram bem a instrução. As hipóteses e o prompt foram fixados antes de rodar a avaliação, e todas as variantes testadas estão na tabela, para não escolher a que por acaso se ajustou melhor a estes 54 textos. A comparação dos classificadores e da abordagem em uso pode ser refeita com `python -m code.modeling.avaliar_sentimento`.

Alternativas consideradas também: modelos generativos maiores (família Llama, por exemplo) pedem vários GB de memória e latência alta sem GPU; ajuste fino próprio exigiria um conjunto rotulado muito maior que o disponível.

Limitações conhecidas: a análise de sentimento quase nunca responde "neutro" (acertou 7% dos neutros na avaliação), então textos informativos tendem a sair como positivos ou negativos; o conjunto de avaliação é pequeno e serve como indicação, não como medida definitiva; o resumidor funciona melhor com textos de notícia completos e pode gerar prefixos estranhos em textos muito curtos ou genéricos. Os dois leem no máximo 512 tokens (cerca de 2.000 caracteres); o excedente é descartado e a resposta da API avisa pelo campo `truncado`.

## Como a integração local foi feita

Os modelos são baixados do HuggingFace na primeira chamada de cada análise e ficam no cache local (`~/.cache/huggingface`, cerca de 1,4 GB no total); depois disso a API funciona sem rede. O carregamento é preguiçoso para a API subir rápido, e cada modelo fica em memória depois de carregado. O sentimento usa o `pipeline` do Transformers; o resumo usa o modelo seq2seq direto com `generate()`, porque o Transformers v5 removeu o pipeline de sumarização.

A rota separa as falhas: se o modelo não carrega, a API responde 503; se carrega mas falha no texto, 500; se o processamento passa de 60 s, 504. O limite de tempo vale só para o processamento, contado a partir do momento em que ele começa; o primeiro download e a espera na fila ficam de fora. Se todos os processadores estiverem ocupados por mais de 30 s, o pedido desiste com 503 em vez de um 504 enganoso. Cada modelo tem sua própria trava de carregamento, então o download de um não atrasa o uso do outro.

## Uso dos dados com LLMs

Situação de cada caso de uso de LLM sobre os dados coletados:

| Caso de uso | Dado de entrada | Situação |
|-------------|-----------------|----------|
| Resumo automático de notícias | Texto completo dos artigos em `data/processed/corpus_noticias.txt` e `corpus_g1.txt` | Entregue no TP4 via `POST /processar_texto` |
| Classificação de sentimento | Títulos e textos das notícias das duas fontes | Entregue no TP4 via `POST /processar_texto` |
| Perguntas e respostas (Q&A) | Corpus de notícias e estatísticas dos focos | Entrega final |
| Geração de relatórios | Agregados de focos por estado, bioma e dia | Entrega final |

Para os casos que faltam, a API já oferece o caminho: um serviço de LLM pode consultar focos e notícias pelas mesmas rotas usadas pela interface.

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Servidor do INPE fora do ar | App sem dados atualizados | Amostra local versionada em `data/raw/`; coleta recua até 5 dias |
| Mudança no formato ou URL dos arquivos | Quebra da coleta | Coleta isolada em `fetch_inpe.py`; fontes alternativas mapeadas no Data Summary Report |
| Sazonalidade (poucos focos na estação chuvosa) | Painel pouco expressivo em certos meses | Usar agregados mensais e históricos nas próximas etapas |
| Mudança no HTML da Agência Brasil ou do G1 | Quebra do scraping | Scrapers isolados em scripts próprios; dados raspados versionados como fallback |
| Busca do G1 mistura a cidade de Queimadas (BA/PB) | Corpus contaminado com assunto fora do tema | Scraper descarta URLs de eleições e links fora do padrão de notícia |
