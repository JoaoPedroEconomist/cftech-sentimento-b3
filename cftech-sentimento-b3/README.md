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
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # preencha ANTHROPIC_API_KEY (ou a chave do provedor usado)
# coloque o snapshot em data/raw/posts.csv (ou .parquet) e a amostra em data/raw/amostra_avaliacao.csv

python -m src.run_pipeline limpeza
python -m src.run_pipeline amostra-rotulos     # cria templates rotulos_A/B.csv
#   -> cada membro rotula SOZINHO e commita ANTES de rodar o LLM
python -m src.run_pipeline kappa-humanos
python -m src.run_pipeline llm --versao v1 --avaliacao
python -m src.run_pipeline llm --versao v2 --avaliacao
python -m src.run_pipeline llm --versao v1      # base inteira
python -m src.run_pipeline llm --versao v2
python -m src.run_pipeline concordancia
python -m src.run_pipeline coordenacao
python -m src.run_pipeline preditivo
pytest -q   # 47 testes
```

Use `--dry-run` no comando `llm` para estimar tokens/custo sem chamar a API.

## 4. Ordem obrigatória (o histórico do Git prova)

1. Manual de rotulagem → 2. rótulos A e B **commitados** → 3. consenso → 4. só então LLM (v1, v2) → 5. kappa e erros → 6. coordenação → 7. teste preditivo → 8. relatório → tag `v1.0`.

## 5. Decisões metodológicas principais

- **Economia de tokens:** posts entram e resultados saem em **TOON** tabular (nomes dos campos uma só vez; ~25–40% menos caracteres que JSON, e o nº de linhas declarado detecta respostas truncadas). Regras fixas do prompt ficam no bloco de sistema com *prompt caching*; justificativa limitada a 15 palavras; posts já classificados vêm do cache em disco. Para volume grande, a Batch API reduz o custo (não implementada).

- **Horário:** posts após o fechamento (17:00 BRT, ajustável em `config.py`) ou em dia sem pregão contam para o **próximo pregão**. O sinal do dia *t* só é cruzado com retornos de *t+1* em diante.
- **Controle de causalidade invertida:** toda regressão inclui o retorno de t (e, na versão robusta, t−1) como controle.
- **Testes pré-definidos** em `docs/plano_de_testes.md` (nº fixo de testes, correção de Holm).
- **Três versões do sinal:** LLM bruto, LLM corrigido (v2) e sem posts coordenados.
- **Erros-padrão:** HAC (Newey-West) com *clusters* por ticker.
- **Privacidade:** `autor_id` já vem anonimizado; textos não vão para README/relatório.

## 6. Resultados

*(preencher ao final: tabela de kappas, principais padrões de falha, clusters, tabela de regressões)*

## 7. Limitações

*(preencher: tamanho da amostra de 100, período curto, liquidez, tickers ambíguos, rótulos de manipulação sem validação externa, etc.)*

## 8. Referências

Ver `docs/referencias.md`.
