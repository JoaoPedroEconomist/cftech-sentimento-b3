# Relatório final — Sentimento, ironia e manipulação (B3)
*3–4 páginas. Exportar para `reports/relatorio.pdf`. Sem texto que identifique autores.*

## 1. Resumo (5 linhas)
Pergunta, dados (período, nº de posts, nº de tickers), principais achados, conclusão sobre poder preditivo.

## 2. Dados e limpeza
Fonte (snapshot anonimizado), filtros, duplicatas removidas, tratamento de fuso, extração de tickers e falsos positivos tratados.

## 3. Rotulagem humana e manual
Kappa A×B: __; categorias com mais divergência: __; como o manual mudou.

## 4. Onde o LLM erra
| Versão | Kappa vs gabarito | Kappa sem ironia | Kappa com ironia | Custo (USD) |
|---|---|---|---|---|
| v1 (zero-shot) | | | | |
| v2 (manual + exemplos) | | | | |

Matriz de confusão (figura). Catálogo dos padrões de falha (tabela: categoria, nº, exemplo **inventado/parafraseado**, por que o LLM errou). Quanto a correção humana (manual/v2) mudou o kappa: __.

## 5. Coordenação e manipulação
Sinais usados e pesos; 30 clusters revisados: __ coordenados, __ provavelmente, __ orgânicos; concordância entre o escore e a decisão humana (precisão@30); exemplos de padrão (parafraseados).

## 6. Poder preditivo
Tabela: versão × variável dependente × modelo → coeficiente, p bruto, p-Holm, n. Resultado do placebo e do controle de retorno passado. Conclusão **honesta**.

## 7. Limitações
Amostra de 100 posts; período; liquidez; tickers ambíguos; rótulos de manipulação sem validação externa; poder estatístico; custos de transação não modelados.

## 8. Conclusões e próximos passos
