# Manual de rotulagem — versão 0.1 (rascunho da dupla; refinar após piloto)

> Uma página. Todos os exemplos são **inventados** pela dupla. Não copie posts da base.
> Rotulem **sozinhos**, sem ver o parceiro nem qualquer LLM.

## Unidade de análise
Um post = um rótulo, referente ao **ticker/empresa principal** mencionado. Se houver vários tickers com posições opostas, rotule o primeiro citado e marque `irrelevante=0`; registre o caso em `docs/decisoes.md`.

## Coluna de saída (CSV `rotulos_X.csv`)
`id, sentimento, ironia, giria_meme, suspeita_coordenacao, irrelevante, observacao`

- `sentimento` ∈ {positivo, neutro, negativo} — posição do **autor** sobre a ação.
- flags ∈ {0, 1}.

## Sentimento
| Rótulo | Quando marcar | Exemplo inventado |
|---|---|---|
| positivo | Expectativa de alta, compra, elogio ao resultado ou à gestão | "Balanço sólido, vou aumentar posição em XXXX3." |
| negativo | Expectativa de queda, venda, crítica | "Tô fora de XXXX4, guidance horrível." |
| neutro | Notícia sem opinião, pergunta, dúvida, dado factual, post sem posição | "XXXX3 divulga resultado quinta às 18h." |

Regras de desempate:
1. **Pergunta não é opinião** → neutro, exceto viés explícito ("Alguém ainda compra esse lixo?" → negativo).
2. **Negação/condicional:** "não acho que cai" → positivo (visão construtiva, sem rótulos intermediários como 'fraco'); "se romper R$ 10 sobe" → neutro (condicional incerto).
3. **Ironia:** rotule sempre a **intenção real**, nunca a literalidade.
4. **Notícia compartilhada com comentário do autor:** rotule estritamente a opinião do **autor**, e não o tom da matéria original. Exemplo: notícia positiva compartilhada com desdém do autor ("sei bem onde isso vai parar...") → negativo.
5. **Dúvida real entre dois rótulos** → escolha **neutro** e escreva a dúvida em `observacao`.

## Flags
- **`ironia`** = 1 quando o sentido literal contradiz a intenção. Pistas: elogio + preço despencando, "parabéns" a quem errou, aspas de escárnio, 🙃😂 com tom negativo. *Ex.: "Que ótimo investir em XXXX3, só perdi 30% 👏".* → negativo, ironia=1.
- **`giria_meme`** = 1 quando o sentido depende de gíria de grupo, meme ou código do fórum (ex.: "foguete", "bag", "mico", "tá todo mundo na mesma boat"). Marque mesmo que você tenha entendido.
- **`suspeita_coordenacao`** = 1 quando o **post isolado** tem sinais de promoção: urgência ("entra agora"), alvo de preço sem argumento, chamada para grupo, texto-padrão. É só suspeita; a decisão sobre campanha é do cluster (etapa 03.5).
- **`irrelevante`** = 1 quando não trata de investimento na ação (spam, ticker ambíguo que é palavra comum, assunto alheio).

## Casos Comuns e Casos de Fronteira (decisões da dupla)
- **Comentário sobre a bolsa em geral:** (ex.: "Ibovespa sangrando hoje com o exterior", "Mercado todo em queda hoje"). Se não houver tese sobre a ação específica, marque **neutro** (ou `irrelevante=1` se o post não tratar do ativo).
- **"Realizei lucro":** (ex.: "Vendi metade das minhas XXXX4 com 20% de ganho, realizei lucro"). Fechamento ou redução de posição vencedora reflete gestão de risco, não pessimismo. Marque **neutro** com `observacao: realizou lucro`.
- **"Vendi tudo":** (ex.: "Vendi tudo de XXXX3, cansei dessa tese", "Zerei posição em XXXX4"). Sinal explícito de encerramento por convicção negativa ou stop loss. Marque **negativo**.
- **Emoji sozinho (🚀 / 📉):** 🚀 isolado → **positivo** + `giria_meme=1`; 📉 isolado → **negativo** + `giria_meme=1`.
- **Post só com link:** neutro, `irrelevante=1` se o link não for legível.
- **Autoironia sobre perda ("sou o rei do prejuízo"):** negativo, ironia=1.
- **Meme de humor sem opinião sobre a ação:** neutro, `giria_meme=1`.

## Processo
1. Piloto de 15 posts **fora** da amostra de avaliação para calibrar este manual.
2. Cada membro rotula os 100 posts da amostra sozinho → `rotulos_A.csv` / `rotulos_B.csv`; commit separado de cada um **antes** de qualquer chamada ao LLM.
3. Calcular kappa A×B (`python -m src.run_pipeline kappa-humanos`), discutir divergências e gerar `rotulos_consenso.csv`.
4. Registrar mudanças do manual em `docs/decisoes.md`.

## Teste do manual
Peça a uma terceira pessoa rotular 10 posts usando só este documento; se divergir muito, o manual não está claro.
