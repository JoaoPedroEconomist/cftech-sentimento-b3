# CF Tech · Case Trainee 06 — Sentimento de redes sociais, ironia e manipulação (B3)

> Repositório **privado**. Nenhum texto de post que identifique o autor deve aparecer neste README, no relatório ou em commits.

## 1. Problema

Fóruns e redes sociais estão cheios de opiniões sobre ações da B3. A tentação é usar um LLM para medir o humor dos investidores e transformá-lo em sinal. Mas o investidor brasileiro escreve com ironia, gíria, meme e emoji, e parte do que parece entusiasmo genuíno é campanha coordenada.

**Pergunta central:** onde o LLM erra ao ler o investidor brasileiro e, depois de corrigido e limpo de manipulação, o sentimento tem algum poder de prever retorno ou volume?

"Não há poder preditivo" é uma resposta aceitável, desde que bem demonstrada.

## 2. Estrutura

```
cftech-sentimento-b3/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/raw/            # snapshot original (nunca editar à mão)
├── data/processed/      # gerado por código
├── notebooks/           # 01_exploracao, 02_llm_e_kappa, 03_preditivo
├── src/                 # funções reutilizáveis
│   ├── config.py        # caminhos, schema, hiperparâmetros fixos
│   ├── limpeza.py       # 03.1 limpeza + tickers
│   ├── rotulagem.py     # 03.2 amostra, kappa entre humanos, consenso
│   ├── toon.py          # codec TOON tabular (entrada/saída do LLM com menos tokens)
│   ├── llm.py           # 03.3 classificação LLM (TOON validado, cache, custo)
│   ├── concordancia.py  # 03.4 kappa, matriz de confusão, catálogo de erros
│   ├── coordenacao.py   # 03.5 escore de suspeita + clusters
│   ├── mercado.py       # preços/volume via yfinance, retorno e volume anormal
│   ├── preditivo.py     # 03.6 índice diário, alinhamento de horário, regressões
│   └── run_pipeline.py  # CLI por etapa
├── prompts/             # sentimento_v1.md, sentimento_v2.md
├── tests/               # pytest
├── reports/             # relatório final e figuras
└── docs/
    ├── manual_rotulagem.md
    ├── plano_de_testes.md   # hipóteses e testes definidos ANTES de rodar
    ├── decisoes.md
    └── relatorio_template.md
```

## 3. Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # No Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # preencha GEMINI_API_KEY (Google Gemini)
# Coloque o snapshot em data/raw/posts.parquet (ou .csv) e a amostra em data/raw/amostra_avaliacao.csv

python -m src.run_pipeline limpeza
python -m src.run_pipeline amostra-rotulos     # cria templates rotulos_A/B.csv
#   -> cada membro rotula SOZINHO e commita ANTES de rodar o LLM
python -m src.run_pipeline kappa-humanos
python -m src.run_pipeline consenso            # gera rotulos_consenso.csv após discussão
python -m src.run_pipeline llm --versao v1 --avaliacao
python -m src.run_pipeline llm --versao v2 --avaliacao
python -m src.run_pipeline llm --versao v1      # base inteira
python -m src.run_pipeline llm --versao v2
python -m src.run_pipeline concordancia
python -m src.run_pipeline coordenacao
python -m src.run_pipeline preditivo
pytest -q   # 59 testes automatizados
```

Use `--dry-run` no comando `llm` para estimar tokens/custo sem chamar a API.

## 4. Ordem obrigatória (o histórico do Git prova)

1. Manual de rotulagem → 2. rótulos A e B **commitados** separadamente → 3. consenso e kappa humano → 4. só então chamadas ao LLM (v1, v2) → 5. kappa, acurácia por ironia e catálogo de erros → 6. detecção de coordenação e revisão humana de clusters → 7. teste preditivo com retorno em excesso do Ibovespa → 8. relatório em PDF → tag `v1.0`.

## 5. Decisões metodológicas principais

- **Modelo de LLM:** **Google Gemini** (`gemini-3.8-flash`) com **temperatura 0 estrita** via `google-genai` SDK, garantindo reprodutibilidade científica.
- **Economia de tokens:** posts entram e resultados saem em formato **TOON tabular** (nomes dos campos uma só vez no cabeçalho; ~25–40% menos caracteres que JSON, com contagem explícita de linhas para detecção imediata de respostas truncadas).
- **Cache determinístico:** cache persistente em disco indexado pela chave composta `id + hash(texto)`, impedindo que posts reais recebam respostas pré-cacheadas de posts de teste.
- **Horário de corte dinâmico da B3:** fechamento regular ajustado automaticamente conforme o calendário de sincronização com o horário de verão dos EUA (18:00 BRT durante o DST nos EUA; 17:00 BRT no restante do ano). Posts após o corte contam para o **próximo pregão**.
- **Retorno anormal / em excesso do Ibovespa:** retornos de fechamento ajustado descontam a variação do Ibovespa (`ret_ativo - ret_ibov`), isolando o humor microeconômico de choques macroeconômicos de mercado.
- **Tratamento de tickers:** sinal principal restrito a posts com um único ticker (`n_tickers == 1`), eliminando ruído de sentimentos antagônicos em um mesmo texto ("vendi X e comprei Y"). Reconhecimento de tickers em minúsculas (ex: `petr4`) e fracionários (`PETR4F` normalizado para `PETR4`). Remoção de falsos positivos da palavra "vale" em expressões verbais idiomáticas ("vale a pena comprar").
- **Coordenação sem viés de futuro (lookahead):**
  - "Pouco histórico" contabiliza estritamente os posts do autor publicados *antes* do instante do cluster.
  - "Rajada" avalia a aceleração de posts em relação ao fluxo médio normal daquele ticker específico.
- **Controle de causalidade invertida:** inclusão de retornos contemporâneos e defasados (`ret_t`, `ret_{t-1}`), acompanhado de teste placebo sobre o retorno passado (`ret_{t-1}`).
- **Correção para múltiplos testes:** correção de Holm aplicada sobre a família de testes dos modelos com controles.

## 6. Resultados e Métricas

- **Testes unitários e de integração:** 59 testes automatizados cobrindo limpeza, fuso horário, integridade de IDs, parsing TOON, cache por chave composta, concordância humana, detecção de ironia, escore de coordenação e regressões em painel com erros-padrão cluster/HAC.
- **Concordância e Análise de Erros:** matrizes de confusão e tabelas comparativas calculam kappa ponderado, acurácia geral e métricas estratificadas por ironia (acurácia e contagem em posts com vs. sem ironia).
- **Poder Preditivo:** avaliado em 18 testes pré-especificados no plano (3 versões × 3 variáveis dependentes × 2 modelos). Critério de decisão pré-definido: evidência de poder preditivo requer significância estatística após Holm (α = 0,05) no modelo com controles, coerência de sinal nas 3 versões e robustez ao controle de `ret_t`.

## 7. Limitações

- **Amostra de avaliação:** amostra de calibração humana de 100 posts reflete a distribuição observada, mas apresenta variância estatística em classes raras (ex.: ironia complexa ou gírias regionais).
- **Dependência de redes sociais:** fóruns e redes públicas sofrem de viés de autosseleção e sobre-representação de investidores de perfil agressivo / especulativo.
- **Ambiguidades semânticas:** abreviações informais e memes com duplo sentido ainda demandam acompanhamento humano de casos de fronteira.
- **Liquidez e microestrutura:** ativos de baixa liquidez apresentam spreads maiores e gaps de negociação que podem amplificar retornos percentuais.

## 8. Referências

Ver `docs/referencias.md`.
