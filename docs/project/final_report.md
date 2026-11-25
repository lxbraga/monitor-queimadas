# Relatório Final: Monitor de Queimadas

Artefato de encerramento do TDSP (Project Final Report), sob responsabilidade do Project Lead.

## O problema

O Brasil sabe onde o fogo está: satélites do INPE registraram 139.642 detecções em três dias de setembro de 2026. O que falta é transformar isso em decisão. Os dados saem em arquivos técnicos, o mesmo incêndio aparece várias vezes, e o número sozinho não explica causa nem contexto. Gestores, ONGs e jornalistas precisam responder rápido três perguntas: onde está pior, onde vai piorar e o que está por trás.

## A solução

Uma aplicação que reúne focos e notícias, trata o que distorce a leitura e responde em linguagem simples.

| Página | Para quem quer |
|--------|----------------|
| Painel | Ver e filtrar os focos por dia, estado, bioma e intensidade |
| Insights | Ver o caminho dos dados, as prioridades e o que os modelos leram nas notícias |
| Assistente | Perguntar em português e seguir a conversa |
| Notícias | Ler o que foi publicado e os temas mais citados |
| Dados | Enviar e baixar CSVs |
| API | Consultar e processar dados por programa |

## O ciclo de ciência de dados

| Etapa | O que foi feito | Artefato |
|-------|-----------------|----------|
| Entendimento do negócio | Problema, público, metas, ODS | [Charter](charter.md) |
| Aquisição | INPE por HTTP, Agência Brasil com Beautiful Soup, G1 com Selenium, sempre dentro do robots.txt | [Data Summary Report](data_summary.md) |
| Preparação | Código de ausência vira vazio, repetidos saem, satélite de referência, texto das notícias ligado à notícia | `code/base_dados.py`, `code/app_utils.py` |
| Modelagem | Sentimento, resumo e assistente com memória | [Model Report](model_report.md) |
| Avaliação | 50 textos para sentimento, três testes para o assistente (95 perguntas), comparação entre versões, testes automatizados | [Model Report](model_report.md), `tests/` |
| Entrega | Dashboard Streamlit e API FastAPI | [Arquitetura](architecture.md) |

## O que os dados mostraram

Focos do satélite de referência, de 19 a 21/09/2026 (3.639 focos):

- **O recorte muda o retrato, e por isso fica à vista.** O Pará lidera na referência (29,1%) e também contando todos os satélites com cada local uma vez por dia (18,7%). Na soma simples, o Tocantins passa à frente por pouco (19,4% contra 18,4%). A liderança do Pará é o achado mais firme; o tamanho da vantagem depende do recorte.
- **Volume e intensidade são problemas diferentes.** O Pará tem mais focos (1.060), com FRP médio de 38,1 MW. Entre os estados com pelo menos 30 focos, o fogo mais intenso está na Bahia (77,1 MW) e no Tocantins (76,2 MW).
- **Onde pode piorar.** Tocantins, Piauí, Ceará, Maranhão, Bahia e Goiás estão com risco de fogo médio na classe crítica. São candidatos a prevenção, mesmo com menos focos que o Pará.
- **Amazônia e Cerrado concentram 94% dos focos** (66,4% e 27,5%). O risco no Cerrado (0,99) é maior que na Amazônia (0,65).
- **O noticiário é sobretudo ruim:** 49 dos 67 títulos foram classificados como negativos. Os positivos precisam de leitura, como explica o Model Report.

São três dias da estação seca. Os números descrevem esse período, não uma tendência. O AQUA passa poucas vezes por dia e oscila: no Amazonas foram 363, 83 e 250 focos. Ele serve melhor para séries longas do que para três dias; foi mantido por ser o critério oficial. O INPE não tinha preenchido o risco de fogo de todos os focos: as médias usam 2.017 dos 3.639, todos dos dois primeiros dias.

## Resultado das metas

| Meta | Resultado |
|------|-----------|
| Coleta automatizada | Atingida: botão no app e script, recuando até 5 dias se o arquivo atrasar |
| Aplicação reprodutível | Atingida no macOS, com instalação limpa; comandos para Windows documentados, mas não testados |
| Cobertura dos dados | Atingida para o arquivo diário; risco e dias sem chuva chegam vazios em parte dos focos |
| Utilidade analítica | Atingida: filtros, mapa, rankings, risco e intensidade |
| Contexto jornalístico | Atingida: 67 notícias de duas fontes, de 2022 a 2026 |
| Acesso programático | Atingida: rotas GET e POST documentadas |
| Análise de texto local | Atingida: sentimento com 76% de acerto, fraco em textos neutros; resumo sem avaliação numérica |
| Comparação correta | Atingida no critério do INPE, com o limite de três dias do satélite de referência explicado em Insights |
| Respostas confiáveis | Medida: 25 de 30 (83%) no teste final, 69% num teste anterior com conversas longas; amostra pequena |
| Adoção | Não medida: faltou teste com usuários do público-alvo |

## ODS e ESG

O projeto fica no pilar Ambiental do ESG.

- **ODS 13, metas 13.1 e 13.3:** dá resposta mais rápida a quem age contra o fogo e torna o dado oficial compreensível para quem não é técnico.
- **ODS 15, metas 15.1 e 15.2:** mostra quais biomas estão sob pressão e com risco alto, o que orienta prevenção em vegetação nativa.

Também há escolhas responsáveis no próprio projeto: modelos pequenos e locais, coleta que respeita o robots.txt, dados públicos e fontes visíveis em cada resposta.

## Como a solução ajuda a decidir

Um roteiro de uso, com os dados entregues:

1. Um gestor abre Insights e vê que o Pará lidera e que o Tocantins está com risco crítico e fogo intenso.
2. No Assistente, pergunta "Qual estado teve mais focos?", depois "E o segundo?" e "Somando os dois, quantos focos?". A resposta foi 1.756, com o aviso de que a conta é do modelo e os valores de origem abertos em "De onde veio".
3. Pergunta sobre a fumaça em Manaus e recebe a explicação com a notícia de origem, para ler por inteiro.
4. No Painel, filtra o estado e baixa os focos para planejar a operação.

## Limitações

- O assistente errou cerca de uma em cada seis perguntas no teste final e pode distorcer relações ao contar notícias, mesmo com números certos. As fontes ficam à vista para conferência.
- Foco de calor não é incêndio confirmado, e o satélite de referência pode falhar em um dia ou passar antes ou depois do fogo.
- As notícias dependem da estrutura dos sites, e a coleta cobre as publicações mais recentes.
- Em computador sem GPU a resposta leva de 7 a 16 s num processador rápido, e o modelo ocupa cerca de 7 GB de memória.

## Próximos passos

- Teste com usuários do público-alvo.
- Séries mensais do INPE, para medir tendência.
- Busca por significado nas notícias, para a pergunta não depender das mesmas palavras.
