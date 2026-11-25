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
- Scraping de página dinâmica com Selenium no G1, que carrega os resultados por JavaScript (`code/data_acquisition/scrape_news_g1.py`), somando uma segunda fonte de notícias ao corpus. No TP4 a coleta trocou a busca do G1 pelas seções de meio ambiente, porque o robots.txt do site proíbe a busca.
- API em FastAPI (`code/api/main.py`) com consulta de focos e notícias (GET) e registro de focos complementares (POST), documentada no Swagger em `/docs` e integrada ao app pela página API.
- Metas reavaliadas: além do painel, o projeto passa a oferecer acesso programático aos dados, o que abre caminho para integrações externas e para os LLMs da próxima etapa.

TP4 (concluído):

- Modelos de linguagem locais integrados à API: análise de sentimento e resumo automático, rodando na própria máquina via HuggingFace Transformers, sem serviços externos.
- Rota `POST /processar_texto` com response models (Pydantic) e respostas estruturadas; as rotas existentes também ganharam response models.
- Tratamento robusto de erros, com mensagem explicativa em cada caso: 400 para texto vazio, 422 para entrada inválida, 500 para falha no processamento, 503 quando o modelo não pode ser carregado e 504 quando o processamento passa de 60 s.
- A resposta avisa (campo `truncado`) quando o texto passa do limite de 512 tokens dos modelos.
- Testes automatizados das rotas e dos códigos de erro em `tests/`.
- Justificativa da escolha dos modelos, hoje no [Model Report](model_report.md).
- Seção "Processar texto" na página API do app, consumindo a nova rota.
- Coletas passam a seguir o robots.txt de cada site, com endereços proibidos bloqueados e o intervalo pedido respeitado.

TP5 (entrega final, concluído):

- Assistente conversacional com memória, sobre os focos e as notícias, com modelo local (página Assistente). Dos caminhos propostos (memória conversacional, sumarização ou agentes), a memória foi a escolhida porque quem analisa queimadas pergunta em sequência: um estado, depois o segundo, depois a comparação. Sumarização já tinha sido entregue no TP4, e agentes pedem modelos maiores do que um notebook roda bem.
- Avaliação do assistente com perguntas de gabarito conhecido e versões sem cada parte do prompt.
- Página Insights, que mostra o caminho da coleta ao resultado dos modelos.
- Satélite de referência do INPE como padrão no Painel, com opção de ver todos.
- Tratamento de valores ausentes e repetidos nos focos.
- Artefatos TDSP completos: este documento, [Data Summary Report](data_summary.md), [Arquitetura](architecture.md), [Model Report](model_report.md) e [Relatório Final](final_report.md).

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
| Comparação correta | Painel e assistente usam o satélite de referência do INPE | Entregue no TP5 |
| Respostas confiáveis | Acerto do assistente em perguntas de teste escritas antes das correções | Medir e informar: 25 de 30 (83%) na versão final |
| Adoção | Feedback de usuários do público-alvo | Não medido: o projeto não foi testado com usuários externos |

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
| Data Preparation | Data Acquisition & Understanding | Limpeza e satélite de referência em `code/base_dados.py` e `code/app_utils.py`, corpus das notícias em `data/processed/` |
| Modeling | Modeling | Sentimento e resumo (`code/api/llm.py`), assistente (`code/analise.py` e `code/assistente.py`), descritos no Model Report |
| Evaluation | Modeling / Acceptance | Avaliações em `code/modeling/`, testes em `tests/` e resultado das metas no Relatório Final |
| Deployment | Deployment | Dashboard em `app.py` e API em `code/api/main.py`, executados localmente |

No diagrama TDSP do enunciado, o Project Charter é artefato do estágio de Business Understanding e o Data Summary Report do estágio de Data Ingest & Understanding. Os demais artefatos do ciclo (arquitetura, Model Report e Relatório Final) ficam na mesma pasta, `docs/project/`.

## Arquitetura

Desenho dos componentes e fluxo dos dados em [architecture.md](architecture.md).

## Alinhamento: dados, IA e engenharia de prompts

O problema tem três partes, e cada uma pede uma peça diferente da solução.

| Parte do problema | Quem responde | Por que essa peça |
|-------------------|---------------|-------------------|
| Os dados existem, mas em arquivos técnicos | Coleta do INPE e das notícias, limpeza e satélite de referência | São 12 satélites vendo o mesmo fogo: 139.642 detecções, que caem para cerca de 35 mil contando cada local de 1 km uma vez por dia. Sem um critério, a conta mede satélites, não fogo. O projeto segue o do INPE e mostra os outros recortes |
| Quem decide não sabe programar nem filtrar planilha | Dashboard e assistente em linguagem natural | Um gestor pergunta "onde está pior?" e segue com "e o segundo?", sem montar filtro |
| Número de foco não diz causa nem contexto | Notícias, com busca, sentimento e resumo | O foco diz onde; a notícia diz por quê e o que está sendo feito |

A engenharia de prompts entra para que o modelo não invente, o que seria grave em política pública. Um modelo pequeno sozinho acertou 4 das 30 perguntas do teste final. Com os dados calculados pelo projeto dentro do prompt, regras e memória, acertou 25. As decisões de prompt e o efeito de cada uma estão no [Model Report](model_report.md).

O uso de modelos é restrito ao que eles fazem bem. Contas, rankings e comparações são feitos com pandas; o modelo só redige. Tudo roda na máquina do usuário: sem custo por consulta e sem enviar perguntas para terceiros.

## Uso dos dados com LLMs

| Caso de uso | Dado de entrada | Situação |
|-------------|-----------------|----------|
| Conversa com memória | Fatos calculados sobre os focos e trechos das notícias | Entregue no TP5, página Assistente |
| Classificação de sentimento | Títulos das notícias das duas fontes | Entregue no TP4 via `POST /processar_texto`; no TP5 aplicada a todo o corpus, página Insights |
| Resumo automático de notícias | Texto completo dos artigos | Entregue no TP4 via `POST /processar_texto` |

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Servidor do INPE fora do ar | App sem dados atualizados | Amostra local versionada em `data/raw/`; coleta recua até 5 dias |
| Mudança no formato ou URL dos arquivos | Quebra da coleta | Coleta isolada em `fetch_inpe.py`; fontes alternativas mapeadas no Data Summary Report |
| Sazonalidade (poucos focos na estação chuvosa) | Painel pouco expressivo em certos meses | Coleta de até 14 dias pelo app; agregados mensais mapeados no Data Summary Report |
| Modelo de linguagem inventar ou distorcer | Decisão baseada em informação errada | Números calculados por código e conferidos depois, fontes visíveis em cada resposta, erros medidos no Model Report |
| Satélite de referência sem passagem ou com falha | Lacuna em um dia ou região | Opção de ver todos os satélites no Painel |
| Mudança no HTML da Agência Brasil ou do G1 | Quebra do scraping | Scrapers isolados em scripts próprios; dados raspados versionados como fallback |
| Filtro por palavras nas seções do G1 aceita títulos fora do tema | Corpus com algumas notícias fora do tema | Filtro exige termos de queimada e descarta usos de fogo fora do tema (vulcões, Círculo de Fogo, garimpo) e notícias de fora do Brasil; limitação documentada no Data Summary Report |
