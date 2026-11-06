# Plano de testes pré-definido (registrado ANTES de rodar o teste preditivo)

> Evita p-hacking. Qualquer alteração depois de ver resultados deve ser registrada em `docs/decisoes.md` e reportada como exploratória.

## Hipóteses
- **H1:** o índice de sentimento do dia *t* (posts até o fechamento) correlaciona com o retorno em *t+1*.
- **H2:** idem para o retorno acumulado de *t+1* a *t+5*.
- **H3:** o volume de posts e/ou o sentimento antecipa volume negociado anormal em *t+1*.

## Variáveis
- `indice = (pos − neg) / total` por ticker-dia (mínimo de `N_MIN_POSTS=3` posts; ver `config.py`).
- **Unidade amostral do sinal principal:** exclusivamente posts com um único ticker (`n_tickers == 1`), evitando contaminação de sentimento entre empresas distintas citadas no mesmo texto.
- `volume_posts` = log(1 + nº de posts).
- `ret_excesso_t+1`, `ret_excesso_acum_t+1_t+5` (**retorno em excesso descontando o Ibovespa**, `ret_ativo - ret_ibov`, em log do fechamento ajustado). Elimina choques e movimentos macroeconômicos comuns de mercado.
- `vol_anormal_t+1` = log(volume) − média móvel de 20 pregões anteriores (janela deslizante sem olhar o futuro, baixando preços 40 dias antes do primeiro post).
- **Controles:** `ret_excesso_t` (retorno do dia do sinal), `ret_excesso_t-1`, `log_volume_posts` (em H1/H2).
- **Horário de corte dinâmico:** posts após o fechamento regular da B3 (17:00 ou 18:00 BRT, ajustado dinamicamente conforme o calendário de sincronização com o horário de verão dos EUA) ou em finais de semana/feriados → atribuídos ao próximo pregão.

## Especificação (única, fixa)
Para cada versão do sinal e cada variável dependente (3 DV):

1. Modelo base: `y_{i,t+h} = a + b·indice_{i,t} + e`
2. Modelo com controles: `y = a + b·indice + g1·ret_t + g2·ret_{t-1} + g3·log_volume_posts + e`
   (em H3: controles = `vol_anormal_t` e `log_volume_posts`; no placebo, só `log_volume_posts`).
3. Erros-padrão **cluster por ticker** (se ≥ 10 tickers) ou HAC (Newey-West, lag 5; `hac-panel` com 2–9 tickers, HAC simples com 1).
4. Efeitos fixos de ticker e de data quando houver tickers e dias suficientes (`--efeitos-fixos`).

## Versões do sinal (3)
1. **LLM bruto:** v1 em todos os posts.
2. **LLM corrigido:** v2 (ou v1 ajustado pela matriz de confusão — `concordancia.ajustar_por_matriz`).
3. **Sem coordenados:** versão corrigida removendo posts em clusters classificados como "coordenado" ou "provavelmente coordenado" na revisão humana.

## Contagem de testes
3 versões × 3 variáveis dependentes × 2 modelos = **18 testes**. Para os coeficientes de `indice` nos 9 testes do modelo com controles (família principal), aplicamos **correção de Holm** e reportamos p-valor bruto e ajustado.

## Critério de decisão
- "Há sinal" = coeficiente de `indice` no modelo **com controles** significativo após Holm (α = 0,05) **e** mesmo sinal nas 3 versões, **e** não desaparece ao incluir `ret_t`.
- Caso contrário concluímos "sem evidência de poder preditivo" e discutimos o poder estatístico (n observações).

## Robustez (declaradas de antemão, rotuladas como secundárias)
- Janela de corte do pregão: 17:00 vs 18:00.
- N_MIN_POSTS = 3 vs 5.
- Excluir tickers ambíguos.
- Subamostra de baixa liquidez.

## Pontos de atenção
- Causalidade invertida (preço → sentimento): controles `ret_t`, `ret_{t-1}`; teste placebo com `ret_{t-1}` como variável dependente (se o índice de *t* "prevê" o retorno **passado**, é sinal de que o índice só segue o preço).
- Sem sobreposição de janelas nos erros: usar HAC no retorno acumulado.
