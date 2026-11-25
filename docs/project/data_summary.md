# Data Summary Report: Monitor de Queimadas

Artefato da fase de Data Acquisition & Understanding do TDSP, sob responsabilidade do Data Scientist. Esboçado no TP1, completado no TP2 com a fonte de notícias, revisado no TP3 com o scraping dinâmico do G1 e os dados recebidos pela API, no TP4 com o uso do corpus pelos modelos de linguagem, e concluído no TP5 com a limpeza, o satélite de referência e o uso final de cada fonte.

## Fontes de dados

| Fonte | Tipo de dado | Formato e acesso | Atualização | Objetivo de uso | Status |
|-------|--------------|------------------|-------------|-----------------|--------|
| INPE, focos diários (Brasil) | Focos de calor por satélite, com localização, município, estado, bioma, risco de fogo e FRP | CSV via HTTP, sem autenticação: `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_AAAAMMDD.csv` | Diária | Fonte principal: Painel, Insights e fatos do Assistente | Em uso |
| Agência Brasil, tag queimadas | Notícias (título, categoria, data, link) e texto completo dos artigos | HTML raspado com Beautiful Soup: `https://agenciabrasil.ebc.com.br/tags/queimadas` | Contínua | Tabela de notícias, nuvem de palavras, sentimento e busca do Assistente | Em uso |
| G1, seções Meio Ambiente e Amazônia | Notícias sobre fogo (título, categoria, data, link) e texto completo dos artigos | Páginas dinâmicas raspadas com Selenium (mais notícias carregam por JavaScript ao clicar em "Mostrar mais"): `https://g1.globo.com/meio-ambiente/` e `.../meio-ambiente/amazonia/` | Contínua | Segunda fonte de notícias para os mesmos usos | Em uso |
| INPE, focos mensais (Brasil) | Agregado mensal dos mesmos focos | CSV via HTTP: `.../focos/csv/mensal/Brasil/focos_mensal_br_AAAAMM.csv` | Mensal | Séries históricas e sazonalidade | Não usada; próximo passo |
| INPE, focos 10 min | Focos quase em tempo real (lat, lon, satélite, data) | CSV via HTTP: `.../focos/csv/10min/` | 10 minutos | Visão ao vivo | Não usada |
| INPE TerraBrasilis (PRODES/DETER) | Desmatamento e alertas por região | API e serviços web públicos | Variável | Cruzar queimadas com desmatamento | Não usada |
| CSVs enviados pelo usuário | Focos complementares no formato do CSV diário do INPE | Upload na própria aplicação | Sob demanda | Complementar a base oficial nos filtros, gráficos e mapa do Painel | Em uso |
| Focos registrados pela API | Focos complementares enviados por `POST /focos` | Gravados em `data/raw/focos_api.csv` (não versionado, gerado em execução) | Sob demanda | Somados às respostas de `GET /focos` | Em uso |

## Dicionário de dados do CSV diário

Arquivo de referência: `data/raw/focos_diario_br_AAAAMMDD.csv`. Os três arquivos entregues (19 a 21/09/2026) têm de 45 a 47 mil registros por dia, somando 139.642 detecções de 12 satélites.

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

Arquivos: `data/raw/noticias_queimadas.csv` (Agência Brasil, gerado por `scrape_news.py`) e `data/raw/noticias_g1.csv` (G1, gerado por `scrape_news_g1.py`). Mesmas colunas nos dois, exceto `estado`, que só o G1 tem.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `titulo` | texto | Título da notícia |
| `categoria` | texto | Editoria da Agência Brasil (Geral, Meio Ambiente, Justiça...) |
| `data` | texto (dd/mm/aaaa) | Data de publicação (no G1, extraída do link da notícia) |
| `estado` | texto (sigla) | Só no G1: estado da notícia regional (como AP ou RO), tirado do início do link; vazio nas notícias das seções nacionais |
| `link` | texto | URL da notícia |

O texto completo dos artigos fica em `data/processed/corpus_noticias.txt` e `data/processed/corpus_g1.txt`, um artigo por bloco. Alimenta a nuvem de palavras e a busca do Assistente, que divide os textos em trechos de até 900 caracteres. Cada bloco do corpus corresponde a uma linha do CSV da mesma fonte, o que permite citar a notícia de cada trecho.

`data/processed/noticias_sentimento.csv` guarda o sentimento de cada título (`sentimento` e `confianca`), gerado por `python -m code.modeling.gerar_sentimento`.

## Qualidade e limitações

- `risco_fogo`, `precipitacao`, `numero_dias_sem_chuva` e `frp` nem sempre vêm preenchidos. No satélite de referência, o dia 21 veio sem risco e sem dias sem chuva; as médias usam só os focos com valor.
- Foco de calor não é sinônimo de incêndio confirmado: nuvens podem ocultar focos e um mesmo incêndio pode gerar vários registros, inclusive em satélites diferentes.
- O arquivo do dia corrente pode sair com atraso; a coleta recua até 5 dias em busca do mais recente disponível.
- O volume de focos varia muito ao longo do ano, com pico na estação seca (julho a outubro).
- Para comparar lugares e datas, o INPE usa só um satélite de referência, o AQUA; o arquivo diário agrega todos ([Infoqueima, INPE](https://dataserver-coids.inpe.br/queimadas/queimadas/Infoqueima/2024/2024_09_infoqueima.pdf)). O Painel começa nele, e Insights e Assistente usam só ele.
- O scraping depende da estrutura HTML das fontes e cobre as páginas mais recentes. Todas as coletas seguem o robots.txt de cada site (`code/data_acquisition/robots.py`): endereços proibidos não são acessados e o intervalo pedido é respeitado, como os 10 segundos entre requisições da Agência Brasil. Por isso o G1 é coletado pelas seções, e não pela busca, que o robots.txt dele proíbe.
- As seções do G1 cobrem vários assuntos, então só ficam os títulos com palavras sobre queimadas e incêndios. "Fumaça" sozinha não basta (aparecia em vulcões e poluição urbana), usos de fogo fora do tema, como "Círculo de Fogo do Pacífico", armas de fogo e dragas de garimpo incendiadas, são descartados, e notícias que citam outro país ou região sem citar o Brasil (como incêndios na Europa) também ficam de fora. Essa última regra vale só para as seções nacionais, que não marcam o lugar da notícia: as regionais (endereço começando pela sigla do estado, como `g1.globo.com/ap/...`) são sempre do Brasil. Por ser um filtro de palavras, algum caso fora do tema ainda pode passar.
- O G1 mostra datas relativas ("há 3 dias"), então a data de publicação vem do próprio link da notícia, que segue o padrão `.../noticia/AAAA/MM/DD/...`. Um link fora desse padrão deixaria o campo vazio; na coleta atual, todas as notícias têm data.
- CSVs enviados por upload são recusados se faltarem colunas ou se coordenadas, datas ou FRP forem inválidos. Ficam só na sessão do usuário e não entram em Insights nem no Assistente.

## Preparação dos dados

Feita na leitura, em `code/base_dados.py`, sem alterar os arquivos originais:

| Problema encontrado | Tratamento |
|---------------------|------------|
| Valor -999 como código de ausência (654 em `risco_fogo`, 332 em `numero_dias_sem_chuva`) | Vira vazio, para não derrubar as médias |
| Registro repetido entre arquivos | Fica um por `id` |
| O mesmo incêndio visto por vários satélites | Comparações usam o AQUA: de 139.642 detecções para 3.639 focos (1.035, 988 e 1.616 por dia) |
| Notícia e texto em arquivos separados | Unidos pela posição, só quando as quantidades coincidem (67 notícias: 42 da Agência Brasil e 25 do G1) |

## Como os dados são integrados

| Dado | Vira | Onde é usado |
|------|------|--------------|
| Focos do INPE | Totais, rankings, FRP, classes de risco e comparações | Painel, Insights, fatos do Assistente |
| Focos completos | Lista de detecções, com a coluna `satelite` | `GET /focos` e opção "Todos" do Painel |
| Títulos das notícias | Sentimento | Insights |
| Textos das notícias | Nuvem de palavras, trechos para busca, resumo | Notícias, Assistente, API |
| Uploads | Linhas somadas à base da sessão | Painel |

Focos e notícias se encontram no Assistente: a pergunta define o assunto, e o prompt recebe os fatos e os trechos desse assunto. Os números das duas fontes não são somados, porque as notícias são de outras datas.

## Dados versionados

Os CSVs do INPE, o CSV de notícias e o corpus ficam versionados em `data/`, servindo de fallback offline para a aplicação. O botão do app e os scripts de coleta atualizam esses arquivos quando há internet.
