# Log de decisões

Formato: **data · o que · por quê · quem**. Registrar também cada vez que vocês discordarem do LLM e por quê.

| Data | Decisão | Por quê | Quem |
|---|---|---|---|
| 2026-10-29 | Corte do pregão em 17:00 BRT (config.py) | Fechamento regular da B3; posts após o corte → próximo pregão | dupla |
| 2026-10-29 | Retornos em log do `Adj Close` | Aditividade para o acumulado D+1..D+5 | dupla |
| 2026-10-29 | Plano de testes fixo em docs/plano_de_testes.md | Evitar p-hacking; 18 testes, Holm na família principal | dupla |
| 2026-10-29 | LLM com temperatura 0, JSON validado por pydantic, cache por `id`+versão do prompt | Reprodutibilidade e custo | dupla |

## Discordâncias humano × LLM
*(preencher durante 03.4: id do post — rótulo humano — rótulo LLM — motivo — categoria de erro)*

## Mudanças de escopo
*(nenhuma até o momento; qualquer mudança deve ser registrada aqui e combinada com a liderança)*
