# Arquitetura da solução: Monitor de Queimadas

Artefato do TDSP sob responsabilidade do Solution Architect.

```mermaid
flowchart LR
    subgraph Fontes
        INPE[INPE: CSV diário de focos]
        AB[Agência Brasil]
        G1[G1: seções de meio ambiente]
    end
    subgraph Coleta
        FI[fetch_inpe.py]
        SN[scrape_news.py<br>Beautiful Soup]
        SG[scrape_news_g1.py<br>Selenium]
        RB[robots.py]
    end
    subgraph Dados
        RAW[(data/raw)]
        PROC[(data/processed)]
    end
    subgraph Preparo
        BD[base_dados.py<br>limpeza e satélite de referência]
        AN[analise.py<br>fatos e busca nas notícias]
    end
    subgraph Modelos locais
        QW[assistente.py<br>Qwen2.5 1,5B]
        LLM[api/llm.py<br>mDeBERTa e PTT5]
    end
    subgraph Uso
        ST[Streamlit: app.py e views]
        API[FastAPI: api/main.py]
    end
    INPE --> FI --> RAW
    AB --> SN --> RAW
    G1 --> SG --> RAW
    RB -.-> SN
    RB -.-> SG
    SN --> PROC
    SG --> PROC
    RAW --> BD
    PROC --> BD
    BD --> AN --> QW --> ST
    BD --> ST
    BD --> API
    LLM --> API --> ST
    LLM -- gerar_sentimento.py --> PROC
```

## Caminho de uma pergunta no Assistente

```mermaid
sequenceDiagram
    actor U as Usuário
    participant P as Página Assistente
    participant A as analise.py
    participant M as Memória da conversa
    participant L as Modelo local
    U->>P: "E o segundo?"
    P->>M: assunto e trocas anteriores
    P->>A: pergunta, focos e memória
    A-->>P: assunto, fatos calculados e trechos de notícias
    alt fora do tema
        P-->>U: recusa, sem chamar o modelo
    else no tema
        P->>L: regras, fatos, notícias, conversa e pergunta
        L-->>P: resposta em partes
        P->>P: confere números e tendências
        P-->>U: resposta, avisos e "De onde veio"
        P->>M: guarda a troca e o assunto
    end
```

## Decisões

| Decisão | Motivo |
|---------|--------|
| Coleta em scripts separados do app | Uma mudança em um site não derruba a aplicação, e os dados versionados servem de reserva |
| Assistente dentro do Streamlit, e não na API | A conversa é da sessão do usuário, e basta um comando para usar. A API continua para acesso programático |
| Modelos locais | Sem custo por uso e sem enviar dados a terceiros |
| Contas fora do modelo | Modelo pequeno erra conta; pandas não |
| Satélite de referência por padrão | É o critério do INPE para comparar lugares e datas |
| `GET /focos` devolve todos os satélites | Quem usa a API recebe a base completa, com a coluna `satelite` para filtrar |
