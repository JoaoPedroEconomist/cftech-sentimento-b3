# Log de decisões

Formato: **data · o que · por quê · quem**. Registrar também cada vez que vocês discordarem do LLM e por quê.

| Data | Decisão | Por quê | Quem |
|---|---|---|---|
| 2026-10-29 | Retornos em log do `Adj Close` | Aditividade para o acumulado D+1..D+5 | dupla |
| 2026-10-29 | Plano de testes fixo em docs/plano_de_testes.md | Evitar p-hacking; 18 testes, Holm na família principal | dupla |
| 2026-10-30 | Troca de Claude para Gemini (gemini-3.8-flash) | Menor latência, custo reduzido e compatibilidade total com a API Google GenAI | dupla |
| 2026-10-30 | Troca de JSON para TOON tabular | Economia de 25% a 40% em tokens/caracteres; integridade de linhas verificada no cabeçalho | dupla |
| 2026-10-30 | LLM com temperatura 0 estrita | Reprodutibilidade científica dos rótulos e atendimento aos critérios do case | dupla |
| 2026-11-06 | Cache com chave composta (id + texto) | Evitar que posts reais recebam respostas de testes anteriores com IDs idênticos | dupla |
| 2026-11-06 | IDs padronizados como texto (astype(str)) | Garantir integridade nas junções entre tabelas de rótulos humanos e LLM | dupla |
| 2026-11-06 | Fuso horário assumido como UTC e convertido para BRT | Dados de redes sociais usam UTC por padrão; convertidos para America/Sao_Paulo | dupla |
| 2026-11-06 | Não apagar textos iguais de autores distintos na limpeza | Textos idênticos de contas diferentes são forte evidência de coordenação/astroturfing | dupla |
| 2026-11-06 | Horário de corte dinâmico da B3 (17h / 18h) | A B3 altera o fechamento para sincronizar com Wall Street durante o horário de verão nos EUA | dupla |
| 2026-11-06 | Retorno em excesso descontando o Ibovespa | Isolar o poder preditivo do sentimento microeconômico de choques macro de mercado | dupla |
| 2026-11-06 | Sinal principal restrito a posts com 1 ticker (n_tickers == 1) | Evitar atribuição espúria de sentimento quando vários ativos aparecem com visões opostas | dupla |
| 2026-11-06 | Download de preços iniciando 40 dias antes do 1º post | Garantir histórico suficiente para calcular os 20 pregões da janela de volume anormal | dupla |
| 2026-11-06 | Histórico do autor sem viés de futuro (lookahead) | "Pouco histórico" contabiliza estritamente os posts publicados antes do cluster analisado | dupla |
| 2026-11-06 | Rajada ponderada pelo movimento normal do ticker | Tickers de alto fluxo não devem gerar falsos positivos de rajada; compara com a média | dupla |

## Discordâncias humano × LLM
*(preencher durante 03.4: id do post — rótulo humano — rótulo LLM — motivo — categoria de erro)*

## Mudanças de escopo
*(nenhuma até o momento; qualquer mudança deve ser registrada aqui e combinada com a liderança)*
