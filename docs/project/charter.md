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

Fica para as próximas etapas: integração com LLMs para resumos em linguagem natural e análises de tendência.

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
| Contexto jornalístico | Notícias raspadas exibidas com nuvem de palavras e estatísticas | Entregue no TP2 |
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
| Data Understanding | Data Acquisition & Understanding | Data Summary Report, `fetch_inpe.py`, `scrape_news.py`, dados em `data/raw/` |
| Data Preparation | Data Acquisition & Understanding | Corpus das notícias em `data/processed/`, agregações no app |
| Modeling | Modeling | Análises e integração com LLMs (próximas etapas) |
| Evaluation | Modeling / Acceptance | Validação dos indicadores contra as metas (próximas etapas) |
| Deployment | Deployment | Dashboard em `app.py`, pronto para o Streamlit Community Cloud |

No diagrama TDSP do enunciado, o Project Charter é artefato do estágio de Business Understanding e o Data Summary Report do estágio de Data Ingest & Understanding. Por isso os dois ficam em `docs/project/`.

## Arquitetura

Coleta em scripts separados: `requests` para os CSVs do INPE e Beautiful Soup para as notícias da Agência Brasil, gravando em `data/raw/` e `data/processed/`. Tratamento com `pandas` e apresentação em Streamlit, com cache e estado de sessão. Deploy previsto no Streamlit Community Cloud a partir do repositório GitHub. Nas etapas futuras, LLM via engenharia de prompts para resumos.

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Servidor do INPE fora do ar | App sem dados atualizados | Amostra local versionada em `data/raw/`; coleta recua até 5 dias |
| Mudança no formato ou URL dos arquivos | Quebra da coleta | Coleta isolada em `fetch_inpe.py`; fontes alternativas mapeadas no Data Summary Report |
| Sazonalidade (poucos focos na estação chuvosa) | Painel pouco expressivo em certos meses | Usar agregados mensais e históricos nas próximas etapas |
| Mudança no HTML da Agência Brasil | Quebra do scraping | Scraper isolado em `scrape_news.py`; dados raspados versionados como fallback |
