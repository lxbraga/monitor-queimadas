# Data Summary Report: Monitor de Queimadas

Artefato da fase de Data Acquisition & Understanding do TDSP, sob responsabilidade do Data Scientist. Esboçado no TP1, completado no TP2 com a fonte de notícias, revisado no TP3 com o scraping dinâmico do G1 e os dados recebidos pela API, e no TP4 com o uso do corpus pelos modelos de linguagem.

## Fontes de dados

| Fonte | Tipo de dado | Formato e acesso | Atualização | Objetivo de uso | Status |
|-------|--------------|------------------|-------------|-----------------|--------|
| INPE, focos diários (Brasil) | Focos de calor por satélite, com localização, município, estado, bioma, risco de fogo e FRP | CSV via HTTP, sem autenticação: `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_AAAAMMDD.csv` | Diária | Fonte principal do painel: filtros, métricas, gráficos e mapa | Em uso |
| Agência Brasil, tag queimadas | Notícias (título, categoria, data, link) e texto completo dos artigos | HTML raspado com Beautiful Soup: `https://agenciabrasil.ebc.com.br/tags/queimadas` | Contínua | Tabela de notícias, nuvem de palavras e estatísticas | Em uso |
| G1, seções Meio Ambiente e Amazônia | Notícias sobre fogo (título, categoria, data, link) e texto completo dos artigos | Páginas dinâmicas raspadas com Selenium (mais notícias carregam por JavaScript ao clicar em "Mostrar mais"): `https://g1.globo.com/meio-ambiente/` e `.../meio-ambiente/amazonia/` | Contínua | Segunda fonte de notícias para tabela, nuvem e estatísticas | Em uso |
| INPE, focos mensais (Brasil) | Agregado mensal dos mesmos focos | CSV via HTTP: `.../focos/csv/mensal/Brasil/focos_mensal_br_AAAAMM.csv` | Mensal | Séries históricas e sazonalidade no dashboard final | Planejado |
| INPE, focos 10 min | Focos quase em tempo real (lat, lon, satélite, data) | CSV via HTTP: `.../focos/csv/10min/` | 10 minutos | Visão ao vivo no dashboard final | Planejado |
| INPE TerraBrasilis (PRODES/DETER) | Desmatamento e alertas por região | API e serviços web públicos | Variável | Cruzar queimadas com desmatamento | Candidata |
| CSVs enviados pelo usuário | Focos complementares no formato do CSV diário do INPE | Upload na própria aplicação | Sob demanda | Complementar a base oficial nos filtros, gráficos e mapa | Em uso |
| Focos registrados pela API | Focos complementares enviados por `POST /focos` | Gravados em `data/raw/focos_api.csv` (não versionado, gerado em execução) | Sob demanda | Somados às respostas de `GET /focos` | Em uso |

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

Arquivos: `data/raw/noticias_queimadas.csv` (Agência Brasil, gerado por `scrape_news.py`) e `data/raw/noticias_g1.csv` (G1, gerado por `scrape_news_g1.py`). Mesmas colunas nos dois.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `titulo` | texto | Título da notícia |
| `categoria` | texto | Editoria da Agência Brasil (Geral, Meio Ambiente, Justiça...) |
| `data` | texto (dd/mm/aaaa) | Data de publicação (no G1, extraída do link da notícia) |
| `link` | texto | URL da notícia |

O texto completo dos artigos fica em `data/processed/corpus_noticias.txt` e `data/processed/corpus_g1.txt`, um artigo por bloco. Alimenta a nuvem de palavras e é o insumo natural das análises com LLM: desde o TP4, qualquer trecho pode ser resumido ou classificado por sentimento em `POST /processar_texto`. Os modelos leem até 512 tokens (cerca de 2.000 caracteres), então artigos longos devem ser enviados em partes.

## Qualidade e limitações

- `risco_fogo`, `precipitacao`, `numero_dias_sem_chuva` e `frp` nem sempre vêm preenchidos; o tratamento será definido na fase de preparação dos dados.
- Foco de calor não é sinônimo de incêndio confirmado: nuvens podem ocultar focos e um mesmo incêndio pode gerar vários registros, inclusive em satélites diferentes.
- O arquivo do dia corrente pode sair com atraso; a coleta recua até 5 dias em busca do mais recente disponível.
- O volume de focos varia muito ao longo do ano, com pico na estação seca (julho a outubro).
- Para contagens oficiais o INPE usa um satélite de referência; o arquivo diário agrega todos.
- O scraping depende da estrutura HTML das fontes e cobre as páginas mais recentes. Todas as coletas seguem o robots.txt de cada site (`code/data_acquisition/robots.py`): endereços proibidos não são acessados e o intervalo pedido é respeitado, como os 10 segundos entre requisições da Agência Brasil. Por isso o G1 é coletado pelas seções, e não pela busca, que o robots.txt dele proíbe.
- As seções do G1 cobrem vários assuntos, então só ficam os títulos com palavras sobre queimadas e incêndios. "Fumaça" sozinha não basta (aparecia em vulcões e poluição urbana), usos de fogo fora do tema, como "Círculo de Fogo do Pacífico", armas de fogo e dragas de garimpo incendiadas, são descartados, e notícias que citam outro país ou região sem citar o Brasil (como incêndios na Europa) também ficam de fora. Por ser um filtro de palavras, algum caso fora do tema ainda pode passar.
- O G1 mostra datas relativas ("há 3 dias"), então a data de publicação vem do próprio link da notícia, que segue o padrão `.../noticia/AAAA/MM/DD/...`. Um link fora desse padrão deixaria o campo vazio; na coleta atual, todas as notícias têm data.
- CSVs enviados por upload são validados apenas pelas colunas; o conteúdo é responsabilidade de quem envia e não persiste ao reiniciar o app.

## Dados versionados

Os CSVs do INPE, o CSV de notícias e o corpus ficam versionados em `data/`, servindo de fallback offline para a aplicação. O botão do app e os scripts de coleta atualizam esses arquivos quando há internet.
