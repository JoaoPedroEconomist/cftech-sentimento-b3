# Relatório Executivo · Sentimento de Redes Sociais, Ironia e Manipulação na B3
**Programa de Trainee CF Tech · Tema 06**  
**Autores:** João Pedro & Equipe Quant CF Tech  
**Data:** Novembro de 2026 | **Tag:** v1.0 | **Status:** Concluído

---

## 1. Resumo Executivo e Síntese de Decisão

O presente estudo investiga a viabilidade empírica de extrair alfa preditivo a partir de sentimento de redes sociais no mercado acionário brasileiro (B3), com foco no tratamento de ironia, coordenação artificial de postagens e validação econométrica rigorosa.

### Principais Conclusões:
1. **Desempenho dos LLMs na B3:** O modelo **Google Gemini Flash Lite** alcançou **Kappa de 0,615** e acurácia de **75,0%** no prompt v2, superando o prompt v1 (Kappa 0,593). O ganho mais expressivo ocorreu no subconjunto de **posts irônicos**, onde a acurácia saltou de **60,0% para 70,0%** (+10 p.p.) com a inclusão de diretrizes explícitas de sarcasmo e gírias do investidor brasileiro.
2. **Eficiência de Custo via TOON:** O uso do formato **TOON tabular** (Topic-Oriented Object Notation) em substituição ao JSON tradicional reduziu o consumo de caracteres em 34%, viabilizando a classificação de 100 posts por menos de **US$ 0,0013** (< R$ 0,01) com 100% de precisão sintática e zero falhas de parsing.
3. **Coordenação vs. Reação Orgânica:** Dos 10 clusters com maior escore de suspeita de coordenação detectados algoritmicamente, **9 foram classificados como falso positivo (orgânicos)** na revisão humana minuciosa. Conclui-se que algoritmos puramente estatísticos baseados em rajada temporal e similaridade textual apresentam baixa precisão no topo em finanças (10% lata), pois fatos relevantes e quedas acentuadas geram rajadas simultâneas espontâneas.
4. **Veredito Preditivo:** Após controle por retornos passados, volume e correção de múltiplos testes de **Holm-Bonferroni**, o sentimento de redes sociais **não apresentou significância estatística** para prever o retorno em excesso do pregão seguinte ($ret_{excesso, t+1}$, $t = -0,65$, $p_{adj} = 1,00$). O teste placebo revelou correlação retrospectiva estatisticamente significativa no modelo bruto ($p = 0,017$), provando que as redes sociais atuam como câmara de eco reativa a perdas passadas e não como antecipadoras de preços futuros.

---

## 2. Metodologia de Coleta, Limpeza e Engenharia de Dados

A base analisada é composta por 100 postagens reais de investidores da B3 coletadas em fóruns e redes sociais (Investing.com, Reddit, Instagram, etc.).

- **Padronização Temporal:** Todos os timestamps foram convertidos para o fuso horário local (`America/Sao_Paulo`), respeitando o horário de mercado.
- **Horário de Corte Dinâmico (B3):** O encerramento do pregão da B3 varia ao longo do ano entre 17:00 e 18:00 BRT devido ao Horário de Verão nos EUA (Daylight Saving Time). O pipeline implementa verificação dinâmica do calendário oficial da B3 para atribuir posts após o fechamento ao pregão do dia útil seguinte sem lookahead bias.
- **Normalização de Tickers:** Suporte a minúsculas (`petr4`) e ativos fracionários (`PETR4F` $ightarrow$ `PETR4`).
- **Desambiguação Semântica de 'Vale':** A expressão verbal comum *"vale a pena"* foi mascarada previamente via regex para impedir falsas atribuições à mineradora Vale S.A. (`VALE3`).
- **Distribuição de Ativos:** 12 tickers foram identificados, com forte concentração em blue chips estatais: **BBAS3** (42 menções) e **PETR4** (40 menções), seguidas por **CMIG4** (10 menções). 7 posts representavam comentários de conjuntura macroeconômica sem ticker específico.

---

## 3. Protocolo de Rotulagem Humana & Concordância (Ground Truth)

Para evitar qualquer viés de confirmação ou ancoragem nos modelos de inteligência artificial, o protocolo de rotulagem humana foi estruturado de forma estritamente independente antes de qualquer consulta à API:

1. **Anotadores A e B:** Dois avaliadores rotularam independentemente a totalidade da amostra (100 posts) para sentimento (`positivo`, `neutro`, `negativo`) e flags binárias (`ironia`, `giria_meme`, `suspeita_coordenacao`, `irrelevante`).
2. **Concordância Inter-Anotador:**
   - **Acurácia Bruta:** **88,0%**
   - **Kappa de Cohen:** **0,811** (faixa de *concordância quase perfeita/substancial*)
   - **Kappa Ponderado Linear:** **0,845**
   - **Kappa de Ironia:** **0,968** (concordância bruta de 99,0%)
3. **Consolidação de Gabarito:** As 31 divergências pontuais (casos de fronteira entre neutro e positivo fraco, ou notícias com tom misto) foram discutidas em sessão de consenso e salvas em `decisoes_consenso.csv`, gerando o gabarito oficial em `rotulos_consenso.csv` (44 neutros, 36 positivos e 20 negativos).

---

## 4. Classificação por LLM: Engenharia de Prompts e Diagnóstico de Erros

Utilizou-se o modelo **Google Gemini Flash Lite** via Google GenAI SDK com **temperatura 0 estrita** para garantir total reprodutibilidade.

| Versão | Modelo | N | Kappa | Kappa Pond. | Acurácia Geral | F1-Macro | Acurácia s/ Ironia (N=80) | Acurácia c/ Ironia (N=20) | Custo Total (USD) |
|---|---|---|---|---|---|---|---|---|---|
| **Prompt v1** | Gemini Flash Lite | 100 | 0,593 | 0,634 | 73,0% | 0,732 | 76,2% | 60,0% | $0,00108 |
| **Prompt v2** | Gemini Flash Lite | 100 | **0,615** | **0,620** | **75,0%** | **0,749** | **76,2%** | **70,0%** | $0,00133 |

### Análise Qualitativa dos Erros e Diretrizes do Prompt v2:
- **Tratamento de Sarcasmo e Emojis:** No prompt v1, posts como *"Mais um dia maravilhoso vendo a ação cair 6%, parabéns aos envolvidos 🤡"* eram classificados como positivos pelo literal das palavras *"maravilhoso"* e *"parabéns"*. O prompt v2 adicionou regras explícitas de inversão de polaridade na presença de emojis contrastantes e hipérboles, elevando a acurácia em ironia em +10 p.p.
- **Realização de Lucros:** O investidor que vende para embolsar lucro costuma celebrar (*"coloquei 30% no bolso, vendi tudo"*). O LLM tendia a classificar como sentimento positivo para o papel, ignorando a pressão vendedora líquida.
- **Erros de Alta Confiança:** Dentre os erros com confiança $\ge 0,80$, o padrão mais recorrente foi a interpretação de compartilhamento de manchetes jornalísticas de fontes corporativas como posicionamento opinativo do autor.

---

## 5. Detecção de Coordenação e Manipulação de Mercado

O módulo de coordenação combina múltiplos sinais em um escore composto:
$$S_{cluster} = 0,35 \cdot S_{similaridade} + 0,25 \cdot S_{rajada} + 0,15 \cdot S_{autor\_novo} + 0,10 \cdot S_{baixa\_liquidez} + 0,15 \cdot S_{urgencia}$$

O pipeline filtrou 10 clusters suspeitos para auditoria humana detalhada:
- **Resultado da Revisão Humana:** 9 clusters classificados como `organico` e 1 cluster classificado como `provavelmente_coordenado` (Cluster C0002 em CMIG4).
- **Precisão do Algoritmo:** Precisão estrita de **0,0%** e precisão lata de **10,0%**.
- **Diagnóstico:** Em ativos líquidos como PETR4 e BBAS3, choques exógenos de mercado (ex: queda súbita de 7% no petróleo, tensão geopolítica internacional) induzem centenas de investidores desarticulados a postar mensagens com vocabulário similar (*"comprei na queda"*, *"hora de encher o carrinho"*). Trata-se de comportamento mimético natural de fórum de varejo, não de cartelização artificial. A intervenção humana na etapa de validação de clusters é indispensável.

---

## 6. Teste Preditivo de Mercado e Econometria em Painel

Para responder à pergunta central — *O sentimento prevê retornos futuros na B3?* —, estimou-se um modelo de regressão em painel com a seguinte especificação:
$$R_{i, t+1}^{excesso} = lpha + eta \cdot IndiceSentimento_{i, t} + \gamma \cdot R_{i, t}^{excesso} + \delta \cdot R_{i, t-1}^{excesso} + 	heta \cdot \ln(VolumePosts_{i, t}) + \epsilon_{i, t+1}$$

Onde $R_{i, t}^{excesso} = R_{i, t}^{ativo} - R_{t}^{Ibovespa}$. Utilizou-se matriz de covariância robusta a heteroscedasticidade e autocorrelação (HAC / Newey-West).

| Especificação | Variável Dependente | Coeficiente ($eta$) | Erro-Padrão (HAC) | Estatística t | p-valor Bruto | p-valor Holm | Conclusão |
|---|---|---|---|---|---|---|---|
| **llm_bruto (v1)** | $ret\_excesso_{t+1}$ | -0,0155 | 0,0174 | -0,89 | 0,3741 | 1,000 | Não significativo |
| **llm_corrigido (v2)**| $ret\_excesso_{t+1}$ | -0,0076 | 0,0117 | -0,65 | 0,5171 | 1,000 | Não significativo |
| **sem_coordenados** | $ret\_excesso_{t+1}$ | -0,0079 | 0,0119 | -0,66 | 0,5100 | 1,000 | Não significativo |
| **Acumulado (5 dias)**| $ret\_excesso\_acum_{t+1:t+5}$ | +0,0105 | 0,0323 | +0,32 | 0,7456 | 1,000 | Não significativo |
| **Volume Anormal** | $vol\_anormal_{t+1}$ | +0,0987 | 0,2549 | +0,39 | 0,6987 | 1,000 | Não significativo |
| **Placebo (Retorno Passado)**| $ret\_excesso_{t-1}$ (v1) | -0,0123 | 0,0051 | -2,39 | **0,0167** | — | **Reatividade a perdas** |

### Conclusões do Teste Econométrico:
1. **Ausência de Poder Preditivo Forward-Looking:** Em nenhuma das janelas futuras ($t+1$ ou acumulado $t+1:t+5$) o coeficiente de sentimento mostrou significância estatística após o controle de Holm ($p_{adj} = 1,00$).
2. **Validação pelo Teste Placebo:** O teste placebo evidenciou correlação negativa entre sentimento e retorno passado no modelo bruto ($t = -2,39, p = 0,0167$). Investidores de redes sociais aumentam queixas e pessimismo após pregões de queda.
3. **Robustez contra Manipulação:** A exclusão dos posts suspeitos de coordenação (`sem_coordenados`) não alterou o resultado substantivo, demonstrando que ruídos coordenados não contaminaram a relação preço-sentimento.

---

## 7. Guia Teórico para a Defesa Oral do Case

- **Por que utilizar TOON em vez de JSON?**  
  O TOON declara os nomes das colunas uma única vez no cabeçalho tabular (`nome[N]{col1,col2}:`), enquanto o JSON repete as chaves em todas as linhas. Isso economiza entre 25% e 40% de tokens de entrada e saída. Além disso, o número fixo de linhas declarado $N$ permite ao validador detectar truncamentos de resposta por limite de max_tokens antes do parsing.
- **Qual a função do teste placebo na modelagem preditiva?**  
  O teste placebo substitui a variável dependente futura pelo retorno passado ($R_{t-1}$). Como o sentimento gerado em $t$ não pode causar retroativamente o preço de $t-1$, qualquer significância observada atesta causalidade reversa (o preço causa o sentimento). Se um modelo alega prever retornos futuros mas falha no placebo sem os devidos controles, os resultados reportados são espúrios.
- **Por que utilizar erros-padrão robustos (HAC / Clusterizado)?**  
  Dados financeiros em painel apresentam forte autocorrelação temporal e dependência transversal entre ativos (ex: choques macroeconômicos afetam Petrobras e Banco do Brasil no mesmo dia). Erros-padrão convencionais de OLS assumem independência idêntica (i.i.d.), o que subestima o erro-padrão real e inflaciona a taxa de falso positivo (erro Tipo I).
- **Como a correção pela matriz de confusão pode contaminar o teste preditivo?**  
  Ajustar as probabilidades de sentimento usando a matriz de confusão calibrada na amostra de avaliação pode introduzir data leakage se as proporções da amostra não refletirem a base populacional, ou se a calibração for aplicada fora de uma janela estritamente temporal do tipo walk-forward.

---

## 8. Recomendações Práticas e Próximos Passos para a Mesa Quant

1. **Descarte de Estratégias Direcionais Simples:** O sentimento agregado de redes de varejo não deve ser usado como sinal isolado de compra/venda de ações na B3 em frequência diária.
2. **Monitoramento de Risco e Assimetria:** O sentimento é útil como indicador de cauda e volatilidade (ex: detecção precoce de crises de reputação ou picos anormais de queixas antes de divulgações de resultados).
3. **Expansão para Dados de Alta Frequência:** Recomenda-se testar a velocidade de absorção do sentimento em horizontes intradiários (15 minutos a 1 hora), onde ineficiências de liquidez do varejo podem oferecer janelas curtas de arbitragem estatística.
