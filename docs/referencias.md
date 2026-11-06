# Referências (do material de apoio fornecido)

Resumo das fontes citadas no documento de literatura. **Confira o texto original antes de citar números no relatório.**

1. *Large Language Models in equity markets: applications, techniques, and insights* (2025) — revisão com 84 estudos (2022–início de 2025). https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1608365/full
2. Liu & Son — *Methods for aggregating investor sentiment from social media* (2024). https://www.nature.com/articles/s41599-024-03434-2 → **uso no projeto:** agregação robusta a duplicatas e contas hiperativas (ponderação por autor).
3. *Systematic review of AI and NLP in social media-based financial ecosystems* (2026) — 29 artigos. https://link.springer.com/article/10.1007/s10791-026-10318-3
4. *AI-Based Sentiment Analysis for Stock Market Prediction: A Systematic Literature Review* (2026) — 87 estudos; verificar qualidade editorial. https://pinnaclepubs.com/index.php/JSPP/article/view/732
5. *On detecting stock price manipulation attacks: a comprehensive systematic literature review* (2025) — 66 artigos. DOI 10.1007/s11042-025-20641-4
6. Deng et al. (2023) — *What do LLMs Know about Financial Markets? A Case Study on Reddit Market Sentiment Analysis*. https://research.google/pubs/what-do-llms-know-about-financial-markets-a-case-study-on-reddit-market-sentiment-analysis/
7. *When bots mislead markets: asymmetric contamination risk in sentiment-based investment decisions* (2026). https://link.springer.com/article/10.1186/s43093-026-00863-0
8. Nam & Skillicorn (2025) — *Detecting Pump & Dump stock market manipulation from online forums*. DOI 10.1007/s42521-024-00121-4 (acurácia 85%, F1 62%: atenção à diferença entre métricas).
9. *FinMoji: emoji-driven sentiment analysis in financial social media* (2026), ACM TWEB. DOI 10.1145/3829331
10. Bisharat & Hean (2026) — *Evaluating Financial Sentiment in the Age of AI* (working paper SSRN 7177498): classificação comparável não implica associação significativa com retorno do dia seguinte.

## Ideias do material de apoio incorporadas
- Três níveis de validação: linguístico (kappa/F1), comportamental (coordenação), econômico (retorno).
- Sentimento aparente ≠ autenticidade ≠ impacto: manter índice de manipulação **separado**, em vez de apenas descontar posts suspeitos.
- Cuidados do backtest: sem vazamento temporal, separação cronológica, comparação com baselines (VADER/FinBERT, opcional), custos de transação se houver estratégia.
