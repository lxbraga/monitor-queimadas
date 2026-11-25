import streamlit as st

st.title("🌱 Sobre o projeto")

st.markdown(
    """
O INPE detecta dezenas de milhares de focos de calor por dia no Brasil, mas
publica esses dados em arquivos técnicos que pouca gente consegue aproveitar.
Quem precisa agir contra as queimadas, como gestores públicos, ONGs e imprensa,
acaba sem uma visão consolidada e atualizada do problema.

Este projeto reúne os focos do INPE e as notícias sobre o tema em um só lugar.
Fica no pilar Ambiental do ESG e atende aos ODS 13 (Ação Contra a Mudança
Global do Clima) e 15 (Vida Terrestre) da Agenda 2030.

### Objetivos

1. Reunir os dados oficiais de queimadas em um só lugar, com coleta automática via API.
2. Mostrar rapidamente quais estados, municípios e biomas concentram mais focos.
3. Apoiar decisões de prevenção e resposta com indicadores objetivos.
4. Aproximar o público geral dos dados oficiais.

Público-alvo: gestores ambientais, ONGs, jornalistas, pesquisadores e cidadãos.

O projeto usa modelos de linguagem que rodam na própria máquina para conversar
sobre os dados (página Assistente), classificar o sentimento das notícias
(página Insights) e resumir textos (página API).

### Links úteis

- [Programa Queimadas (INPE)](https://terrabrasilis.dpi.inpe.br/queimadas/portal/): fonte oficial dos dados
- [Dados abertos de focos de calor (INPE)](https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/): arquivos consumidos pelo projeto
- [Agência Brasil](https://agenciabrasil.ebc.com.br/tags/queimadas): fonte das notícias (Beautiful Soup)
- [G1 Meio Ambiente](https://g1.globo.com/meio-ambiente/): fonte das notícias (Selenium)
- [Agenda 2030 e os 17 ODS (ONU Brasil)](https://brasil.un.org/pt-br/sdgs)
- [Conecta Brasil](https://conectabrasil.org/home): inspiração de iniciativas sociais
- [Observatório do Terceiro Setor](https://observatorio3setor.org.br/carrossel/lista-conheca-projetos-sociais-de-15-causas-diferentes/): inspiração de iniciativas sociais
"""
)
