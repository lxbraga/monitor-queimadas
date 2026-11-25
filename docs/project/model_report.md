# Model Report: Monitor de Queimadas

Artefato da fase de Modeling do TDSP, sob responsabilidade do Data Scientist. Descreve os modelos usados, como foram escolhidos, como os prompts foram construídos e o que a avaliação mostrou.

## Visão geral

| Uso | Modelo | Licença | Onde | Custo |
|-----|--------|---------|------|-------|
| Assistente com memória | `Qwen/Qwen2.5-1.5B-Instruct` | Apache 2.0 | `code/assistente.py`, página Assistente | ~3 GB de download |
| Sentimento | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | MIT | `code/api/llm.py`, página Insights e API | ~530 MB |
| Resumo | `recogna-nlp/ptt5-base-summ` | MIT | `code/api/llm.py`, API | ~890 MB |

Todos rodam localmente com HuggingFace Transformers. Não há chamada paga nem texto enviado para fora da máquina.

## Assistente com memória

### Por que este modelo

O modelo precisa seguir instruções em português, caber num notebook sem placa de vídeo e ter licença aberta. O Qwen2.5 1,5B atende aos três; a versão de 0,5B fica como alternativa para máquinas com pouca memória (variável `MODELO_ASSISTENTE`), sem avaliação própria. Modelos de 7B ou mais responderiam melhor, mas passam de 14 GB de memória e ficam lentos em CPU.

Tempo por resposta, medido num MacBook com M3 Max: mediana de 1,2 s e máximo de 2,1 s no teste 3 na GPU integrada; só em CPU, duas respostas medidas, de 7 s e 16 s, com a primeira palavra entre 3 e 5 s. Pico de 7,3 GB de RAM em CPU. Em notebooks comuns deve ser mais lento.

### Como uma resposta é montada

1. **Assunto.** O código identifica estados, biomas e municípios citados e se a pergunta é de dados ou de notícia. Sem lugar citado, vale o da pergunta anterior.
2. **Fatos.** Totais, rankings, FRP, risco e comparações são calculados com pandas, só no satélite de referência, e entram no prompt já em texto.
3. **Notícias.** Busca BM25 nos trechos das 67 notícias. Foi preferida a uma busca por embeddings por dispensar mais um modelo na memória, num corpus pequeno.
4. **Memória.** As cinco últimas trocas vão inteiras; as anteriores, resumidas em uma linha cada. O assunto atual e os últimos três lugares citados também ficam guardados, para entender "e o segundo?" e "qual dos dois?".
5. **Geração.** Sem sorteio (`do_sample=False`), para a mesma conversa dar a mesma resposta.
6. **Conferência.** Todo número da resposta é procurado no material. O que sai de uma conta simples é marcado como conta do modelo; o que não aparece em lugar nenhum vira aviso na tela. Palavras de tendência ("aumento", "queda") que o material não traz também.

Pergunta fora do tema, ou sobre focos de uma data que a base não cobre, é recusada pelo código, sem chamar o modelo, e não entra na memória.

### Engenharia de prompts

O prompt nasceu simples e cada parte foi incluída por causa de um erro visto nas conversas de desenvolvimento.

| Erro observado | O que mudou no prompt ou em volta dele |
|----------------|----------------------------------------|
| Inventava prazos e tendências ("últimas três horas", "aumento significativo") | Regras 2 e 6, e a conferência de tendência |
| Respondia de conhecimento próprio | Regra 1, regra 4 com a frase exata de recusa e bloqueio fora do tema por código |
| Esquecia as regras em prompts longos | Lembrete curto junto da pergunta, no fim |
| Pegava o total do país em vez do estado | Fatos do lugar perguntado vêm antes dos gerais |
| Lia "risco de fogo médio 1,00" como risco médio | Material diz "classe CRÍTICO (índice 1,00 de 1)", sem a palavra "médio" |
| Dava número de notícia para data fora da base | Data fora do período é recusada por código |
| Errava "qual tem menos?" e "e o segundo?" | A posição pedida é calculada e vai junto da pergunta |
| Errava "qual dos dois teve mais?" | Comparação pronta, calculada, ao lado da pergunta, dita só no sentido perguntado |
| Misturava números de notícia com os dos focos | Regra 3, e notícia só entra se for relevante para a pergunta |
| Confundia "1º" e "2º" do ranking com quantidades | Ordinais retirados do material |

O texto completo do prompt está em `REGRAS` e `LEMBRETE`, em `code/assistente.py`.

### Avaliação

As perguntas e gabaritos estão em `data/processed/avaliacao_assistente.json`, em conversas, porque a memória só é testada em sequência. Cada teste foi escrito antes das correções que ele mede e rodado uma vez; depois virou material de desenvolvimento. A correção automática foi revista à mão, com o motivo de cada mudança registrado.

| Teste | Conversas | Acertos, depois da revisão |
|-------|-----------|----------------------------|
| 1 | Curtas, até 4 perguntas | 22 de 26 (85%) |
| 2 | Até 14 perguntas | 27 de 39 (69%); a versão do teste 1, nas mesmas perguntas, fez 24 |
| 3 (versão final) | Até 12 perguntas | **25 de 30 (83%)** |

O teste 1 era otimista: só tinha conversas curtas. O 2 mostrou três falhas que ele não via (classe de risco trocada, data fora da base respondida com número de notícia e assunto estranho aceito no meio da conversa) e outras nas perguntas de "qual tem mais" e "qual tem menos". O 3 mede a versão entregue.

| Versão, no teste 3 | Dados | Memória | Notícias | Recusa | Total |
|--------------------|-------|---------|----------|--------|-------|
| **Em uso** | 10/11 | 6/9 | 3/4 | 6/6 | **25/30** |
| Sem as regras do prompt | 11/11 | 6/9 | 2/4 | 6/6 | 25/30 |
| Sem memória | 10/11 | 0/9 | 3/4 | 6/6 | 19/30 |
| Sem os dados do projeto | 0/11 | 0/9 | 1/4 | 3/6 | 4/30 |

Leitura dos resultados:

- O que mais pesa é o material do projeto: sem ele, 4 de 30.
- A memória decide as perguntas de continuação: 6 de 9 com ela, nenhuma sem.
- As regras do prompt não mudaram o total neste teste. Com a conta pronta e as recusas no código, sobra menos para elas. Ficaram porque as respostas saem mais curtas e com menos invenção: no desenvolvimento, 1 resposta com número sem origem, contra 4 sem as regras.
- São 30 perguntas, escritas e corrigidas dentro do próprio projeto. Serve para comparar versões e achar falhas, não como medida definitiva.

Erros da versão em uso no teste 3: "Qual dos dois teve menos focos?" (inverteu), "Qual foi a primeira pergunta que eu fiz?" (recusou), "Há quanto tempo não chove no Ceará?" (misturou dois números), "E o Amazonas?" depois de perguntar o dia do Pará (usou o país) e "O que aconteceu em Tartarugalzinho?" (não encontrou).

Para refazer: `python -m code.modeling.avaliar_assistente teste`. São 120 respostas, cerca de 4 minutos num M3 Max. Resultados em `resultado_avaliacao_assistente_teste_revisado.csv` (teste 3) e `resultado_avaliacao_assistente_segundo_teste.csv`.

### Limitações

- Em notícias, o modelo pode ligar números certos ao fato errado. No teste 2, disse que 61,25% dos focos do Brasil eram da Terra Indígena Kayapó; a notícia falava da parcela dos focos da própria terra registrada em setembro. A conferência automática vê números, não relações entre eles. Por isso cada resposta mostra de onde veio.
- Perguntas gerais de conhecimento que coincidem com palavras das notícias ainda passam ("Qual a capital da França?").
- A busca é por palavras, sem entender significado.
- O assistente conhece só o período de focos carregado e as notícias coletadas.

## Sentimento e resumo

Critérios usados: desempenho na tarefa em português, custo computacional para rodar localmente (CPU de um notebook, sem GPU dedicada) e acessibilidade (download aberto pelo HuggingFace, carregável com a biblioteca Transformers). Dois modelos atendem às duas análises do projeto:

| Tarefa | Modelo | Por que ele |
|--------|--------|-------------|
| Sentimento | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, em classificação zero-shot | Modelo de inferência textual treinado em mais de 100 idiomas, incluindo português. Em vez de um classificador de sentimento pronto, ele julga qual hipótese o texto confirma: "Esta notícia é positiva", "negativa" ou "neutra". Foi a abordagem que melhor entendeu notícias sobre queimadas na avaliação abaixo; ~530 MB, de 60 a 120 ms por texto em CPU |
| Resumo | `recogna-nlp/ptt5-base-summ` | PTT5 (T5 pré-treinado em português pelo grupo Recogna/Unesp) ajustado para sumarização de notícias, exatamente o domínio do corpus; ~890 MB, resume em 1 a 5 s em CPU |

### Avaliação do sentimento

O primeiro modelo escolhido, um classificador de sentimento multilíngue (DistilBERT), errava notícias boas sobre queimadas: palavras como "incêndio", "fumaça" e "focos" puxavam o resultado para negativo, e quase todo texto do projeto tem essas palavras. Para escolher com dados, montamos um conjunto rotulado em `data/processed/avaliacao_sentimento.csv`, com 50 textos (20 negativos, 20 positivos e 10 neutros): 29 títulos reais das notícias raspadas e 21 frases escritas no mesmo estilo, positivas e neutras, com vocabulário de fogo. Os rótulos foram atribuídos manualmente com um critério fixo: positivo é notícia boa para o meio ambiente e a população (queda de focos, controle, recuperação), negativo é notícia ruim (aumento, recorde, dano) e neutro é informativa ou procedimental. Numa segunda revisão, saíram quatro títulos que misturavam um fato ruim com uma reação (como "Após avanço das queimadas, Ibama inicia fiscalização"), porque admitiam mais de um rótulo.

| Abordagem | Acerto | F1 macro | Positivos | Neutros | Negativos | ms por texto |
|-----------|--------|----------|-----------|---------|-----------|--------------|
| **Zero-shot mDeBERTa, hipótese "Esta notícia é {}." (em uso)** | **76%** | **0,62** | **85%** | 10% | **100%** | 58 a 116 |
| Classificador XLM-R (`cardiffnlp/twitter-xlm-roberta-base-sentiment`) | 52% | 0,48 | 15% | 100% | 65% | 58 |
| Zero-shot mDeBERTa, hipótese "Esta é uma notícia {}." | 52% | 0,45 | 50% | 0% | 80% | 57 |
| LLM Qwen2.5 0,5B com instrução | 56% | 0,41 | 100% | 0% | 40% | 182 |
| LLM Qwen2.5 1,5B com instrução | 52% | 0,36 | 30% | 0% | 100% | 417 |
| Classificador DistilBERT (`lxyuan/...-sentiments-student`, escolha anterior) | 40% | 0,29 | 30% | 0% | 70% | 36 |
| Classificador BERTweet-pt (`pysentimiento/bertweet-pt-sentiment`) | 30% | 0,26 | 0% | 100% | 25% | 28 |
| Classificador DistilBERT multilíngue (`tabularisai/multilingual-sentiment-analysis`) | 24% | 0,18 | 0% | 100% | 10% | 32 |

Os tempos variam entre execuções conforme a carga da máquina. Os classificadores prontos foram treinados com tweets e avaliações de produtos, onde vocabulário de fogo quase sempre indica algo ruim; os LLMs pequenos não seguiram bem a instrução. As hipóteses e o prompt foram fixados antes de rodar a avaliação, e todas as variantes testadas estão na tabela, para não escolher a que por acaso se ajustou melhor a estes textos. A comparação dos classificadores e da abordagem em uso pode ser refeita com `python -m code.modeling.avaliar_sentimento`.

Alternativas consideradas também: modelos generativos maiores (família Llama, por exemplo) pedem vários GB de memória e latência alta sem GPU; ajuste fino próprio exigiria um conjunto rotulado muito maior que o disponível.

Limitações conhecidas: a análise de sentimento quase nunca responde "neutro" (acertou 1 dos 10 neutros na avaliação), então textos informativos tendem a sair como positivos ou negativos; o conjunto de avaliação é pequeno e serve como indicação, não como medida definitiva; o resumidor funciona melhor com textos de notícia completos e pode gerar prefixos estranhos em textos muito curtos ou genéricos. Os dois leem no máximo 512 tokens (cerca de 2.000 caracteres); o excedente é descartado e a resposta da API avisa pelo campo `truncado`.

### Integração local

Os modelos são baixados do HuggingFace na primeira chamada de cada análise e ficam no cache local (`~/.cache/huggingface`, cerca de 1,4 GB no total); depois disso a API funciona sem rede. O carregamento é preguiçoso para a API subir rápido, e cada modelo fica em memória depois de carregado. O sentimento usa o `pipeline` do Transformers; o resumo usa o modelo seq2seq direto com `generate()`, porque o Transformers v5 removeu o pipeline de sumarização.

A rota separa as falhas: se o modelo não carrega, a API responde 503; se carrega mas falha no texto, 500; se o processamento passa de 60 s, 504. O limite de tempo vale só para o processamento, contado a partir do momento em que ele começa; o primeiro download e a espera na fila ficam de fora. Se todos os processadores estiverem ocupados por mais de 30 s, o pedido desiste com 503 em vez de um 504 enganoso. Cada modelo tem sua própria trava de carregamento, então o download de um não atrasa o uso do outro.

### Sentimento aplicado ao corpus

No TP5 o modelo classificou os títulos das 67 notícias (`code/modeling/gerar_sentimento.py`), o tipo de texto em que foi avaliado: 49 negativas, 18 positivas e nenhuma neutra. Na leitura dos 18 títulos, 7 são de fato boas notícias, 7 são informativas e 4 são ruins ou fora do tema, como "Amapá registra mais de mil focos de calor em 48 horas; número é 176% maior". É o viés já visto na avaliação: sem a classe neutra, o que não é claramente ruim vira positivo. A página Insights avisa disso e lista as notícias para conferência.
