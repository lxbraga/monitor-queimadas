# Data Summary Report: Monitor de Queimadas

Artefato da fase de Data Acquisition & Understanding do TDSP, sob responsabilidade do Data Scientist. Esboçado no TP1 e completado no TP2 com a fonte de notícias.

## Fontes de dados

| Fonte | Tipo de dado | Formato e acesso | Atualização | Objetivo de uso | Status |
|-------|--------------|------------------|-------------|-----------------|--------|
| INPE, focos diários (Brasil) | Focos de calor por satélite, com localização, município, estado, bioma, risco de fogo e FRP | CSV via HTTP, sem autenticação: `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_AAAAMMDD.csv` | Diária | Fonte principal do painel: filtros, métricas, gráficos e mapa | Em uso |
| Agência Brasil, tag queimadas | Notícias (título, categoria, data, link) e texto completo dos artigos | HTML raspado com Beautiful Soup: `https://agenciabrasil.ebc.com.br/tags/queimadas` | Contínua | Tabela de notícias, nuvem de palavras e estatísticas por categoria e ano | Em uso |
| INPE, focos mensais (Brasil) | Agregado mensal dos mesmos focos | CSV via HTTP: `.../focos/csv/mensal/Brasil/focos_mensal_br_AAAAMM.csv` | Mensal | Séries históricas e sazonalidade no dashboard final | Planejado |
| INPE, focos 10 min | Focos quase em tempo real (lat, lon, satélite, data) | CSV via HTTP: `.../focos/csv/10min/` | 10 minutos | Visão ao vivo no dashboard final | Planejado |
| INPE TerraBrasilis (PRODES/DETER) | Desmatamento e alertas por região | API e serviços web públicos | Variável | Cruzar queimadas com desmatamento | Candidata |
| CSVs enviados pelo usuário | Focos complementares no formato do CSV diário do INPE | Upload na própria aplicação | Sob demanda | Complementar a base oficial nos filtros, gráficos e mapa | Em uso |

## Dicionário de dados do CSV diário

Arquivo de referência: `data/raw/focos_diario_br_AAAAMMDD.csv`. Na estação seca chega a ter cerca de 30 mil registros por dia.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | texto (UUID) | Identificador único do foco |
| `lat`, `lon` | numérico | Coordenadas do foco em graus decimais |
| `data_hora_gmt` | data/hora | Instante da detecção (GMT) |
| `satelite` | texto | Satélite que detectou o foco |
| `municipio`, `estado`, `pais` | texto | Localização administrativa |
| `municipio_id`, `estado_id`, `pais_id` | numérico | Códigos das unidades administrativas |
| `numero_dias_sem_chuva` | numérico | Dias consecutivos sem chuva no local (pode vir vazio) |
| `precipitacao` | numérico | Precipitação acumulada em mm (pode vir vazio) |
| `risco_fogo` | numérico | Índice de risco de fogo do INPE, de 0 a 1 (pode vir vazio) |
| `bioma` | texto | Bioma do foco |
| `frp` | numérico | Fire Radiative Power em MW, intensidade do fogo (pode vir vazio) |

## Dicionário de dados das notícias

Arquivo: `data/raw/noticias_queimadas.csv`, gerado por `code/data_acquisition/scrape_news.py`.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `titulo` | texto | Título da notícia |
| `categoria` | texto | Editoria da Agência Brasil (Geral, Meio Ambiente, Justiça...) |
| `data` | texto (dd/mm/aaaa) | Data de publicação |
| `link` | texto | URL da notícia |

O texto completo dos artigos fica em `data/processed/corpus_noticias.txt`, um artigo por bloco, usado na nuvem de palavras.

## Qualidade e limitações

- `risco_fogo`, `precipitacao`, `numero_dias_sem_chuva` e `frp` nem sempre vêm preenchidos; o tratamento será definido na fase de preparação dos dados.
- Foco de calor não é sinônimo de incêndio confirmado: nuvens podem ocultar focos e um mesmo incêndio pode gerar vários registros, inclusive em satélites diferentes.
- O arquivo do dia corrente pode sair com atraso; a coleta recua até 5 dias em busca do mais recente disponível.
- O volume de focos varia muito ao longo do ano, com pico na estação seca (julho a outubro).
- Para contagens oficiais o INPE usa um satélite de referência; o arquivo diário agrega todos.
- O scraping depende da estrutura HTML da Agência Brasil e cobre as páginas mais recentes da tag; é executado com pausa entre requisições e User-Agent identificado.
- CSVs enviados por upload são validados apenas pelas colunas; o conteúdo é responsabilidade de quem envia e não persiste ao reiniciar o app.

## Dados versionados

Os CSVs do INPE, o CSV de notícias e o corpus ficam versionados em `data/`, servindo de fallback offline para a aplicação. O botão do app e os scripts de coleta atualizam esses arquivos quando há internet.
