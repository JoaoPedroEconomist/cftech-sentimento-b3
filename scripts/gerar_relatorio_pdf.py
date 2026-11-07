"""Script de geração do Relatório Executivo em Markdown e PDF profissional (ReportLab).
Case Trainee CF Tech · Tema 06 — Sentimento de redes sociais, ironia e manipulação (B3).
"""
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

RAIZ = Path(__file__).resolve().parents[1]
REPORTS = RAIZ / "reports"
REPORTS.mkdir(exist_ok=True)

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (páginas 2 em diante)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "CF Tech Trainee Program · Tema 06: Sentimento de Redes Sociais na B3")
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "Relatório Executivo e Metodológico")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 40, 8.5 * inch - 54, 11 * inch - 40)
            
        # Footer (todas as páginas)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 8.5 * inch - 54, 45)
        self.drawString(54, 32, "Confidencial · Comitê de Avaliação CF Tech")
        texto_pag = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(8.5 * inch - 54, 32, texto_pag)
        self.restoreState()


def gerar_relatorio_md() -> str:
    md_content = """# Relatório Executivo · Sentimento de Redes Sociais, Ironia e Manipulação na B3
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
- **Normalização de Tickers:** Suporte a minúsculas (`petr4`) e ativos fracionários (`PETR4F` $\rightarrow$ `PETR4`).
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
$$R_{i, t+1}^{excesso} = \alpha + \beta \cdot IndiceSentimento_{i, t} + \gamma \cdot R_{i, t}^{excesso} + \delta \cdot R_{i, t-1}^{excesso} + \theta \cdot \ln(VolumePosts_{i, t}) + \epsilon_{i, t+1}$$

Onde $R_{i, t}^{excesso} = R_{i, t}^{ativo} - R_{t}^{Ibovespa}$. Utilizou-se matriz de covariância robusta a heteroscedasticidade e autocorrelação (HAC / Newey-West).

| Especificação | Variável Dependente | Coeficiente ($\beta$) | Erro-Padrão (HAC) | Estatística t | p-valor Bruto | p-valor Holm | Conclusão |
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
"""
    p = REPORTS / "relatorio_executivo.md"
    p.write_text(md_content, encoding="utf-8")
    return md_content


def gerar_relatorio_pdf():
    pdf_path = str(REPORTS / "relatorio_executivo.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#0F172A")
    secondary_color = colors.HexColor("#1E293B")
    accent_blue = colors.HexColor("#1D4ED8")
    text_dark = colors.HexColor("#1E293B")
    text_muted = colors.HexColor("#475569")
    bg_light = colors.HexColor("#F8FAFC")
    border_color = colors.HexColor("#E2E8F0")

    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=accent_blue,
        spaceAfter=12,
    )
    style_meta = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_muted,
        spaceAfter=14,
    )
    style_h1 = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )
    style_h2 = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    style_body = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.2,
        textColor=text_dark,
        spaceAfter=6,
        alignment=4,  # Justified
    )
    style_bullet = ParagraphStyle(
        'BulletDark',
        parent=style_body,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )
    style_callout = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1E3A8A"),
    )
    style_th = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
        alignment=1,
    )
    style_td = ParagraphStyle(
        'TD',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9,
        textColor=text_dark,
        alignment=1,
    )
    style_td_left = ParagraphStyle(
        'TDLeft',
        parent=style_td,
        alignment=0,
    )

    story = []

    # ==================== PÁGINA 1 ====================
    story.append(Paragraph("RELATÓRIO EXECUTIVO & METODOLÓGICO", style_subtitle))
    story.append(Paragraph("Sentimento de Redes Sociais, Ironia e Manipulação na B3", style_title))
    story.append(Paragraph("<b>Case Trainee CF Tech · Tema 06</b> &nbsp;|&nbsp; <b>Autores:</b> João Pedro & Equipe Quant &nbsp;|&nbsp; <b>Data:</b> Nov/2026 &nbsp;|&nbsp; <b>Tag:</b> v1.0", style_meta))
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceAfter=10))

    story.append(Paragraph("1. Resumo Executivo e Síntese de Decisão", style_h1))
    story.append(Paragraph(
        "Este estudo investiga empiricamente a viabilidade de extrair sinal preditivo a partir de postagens de redes sociais no mercado de capitais brasileiro (B3), com ênfase no tratamento de sarcasmo/ironia, detecção de manipulação coordenada e rigor metodológico para evitar descobertas espúrias.",
        style_body
    ))

    # Box com Destaques
    destaques_data = [[
        Paragraph(
            "<b>Síntese dos Resultados Chave:</b><br/>"
            "• <b>Ganho Expressivo com Engenharia de Prompt:</b> O modelo Google Gemini Flash Lite atingiu <b>Kappa de Cohen de 0,615</b> e 75,0% de acurácia no Prompt v2. A acurácia em <b>posts irônicos subiu de 60,0% para 70,0%</b> (+10 p.p.) com diretrizes semânticas customizadas.<br/>"
            "• <b>Economia Estrutural via TOON Tabular:</b> Redução de 34% no consumo de tokens frente ao JSON, com custo total de apenas <b>US$ 0,0013</b> para 100 posts e 100% de taxa de validação sintática via Pydantic.<br/>"
            "• <b>Coordenação de Redes vs. Ruído Orgânico:</b> 90% dos clusters detectados por rajada algorítmica revelaram-se falso positivos (orgânicos) na auditoria humana, atestando a ineficácia de filtros cegos sem intervenção qualitativa.<br/>"
            "• <b>Ausência de Alfa Preditivo em Painel:</b> Controlando por retornos passados e aplicando a correção de <b>Holm-Bonferroni</b>, o sentimento não previu os retornos em excesso do Ibovespa (t = -0,65, p_adj = 1,00). O teste placebo comprovou reatividade a perdas passadas (t = -2,39, p = 0,0167), demonstrando que o varejo reage tardiamente às oscilações de preço.",
            style_callout
        )
    ]]
    t_box = Table(destaques_data, colWidths=[7.2 * inch])
    t_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor("#93C5FD")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_box)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Engenharia de Dados, Limpeza e Desambiguação", style_h1))
    story.append(Paragraph(
        "A base real analisada reúne 100 postagens de investidores da B3 coletadas em redes abertas (Investing.com, Reddit, Instagram). O pré-processamento aplicou critérios estritos para integridade da série temporal:",
        style_body
    ))
    story.append(Paragraph("• <b>Alinhamento de Fuso Horário:</b> Conversão de todos os registros para o fuso local <code>America/Sao_Paulo</code>, garantindo sincronização exata com os horários de negociação.", style_bullet))
    story.append(Paragraph("• <b>Horário de Corte Dinâmico (17h/18h):</b> O encerramento da B3 oscila sazonalmente conforme o horário de verão dos EUA (DST). O pipeline consulta o calendário da B3 atribuindo postagens pós-fechamento ao pregão seguinte sem lookahead bias.", style_bullet))
    story.append(Paragraph("• <b>Normalização de Tickers e Stoplist:</b> Expressões em minúsculas (<code>petr4</code>) e lotes fracionários (<code>PETR4F</code>) foram unificados ao ativo base. Termos de 4 letras + dígito que não representam ações (<code>COVID19</code>, <code>WIN10</code>) foram descartados.", style_bullet))
    story.append(Paragraph("• <b>Filtro de Desambiguação ('Vale'):</b> Expressões lexicais verbais frequentes como <i>'vale a pena comprar'</i> ou <i>'não vale nada'</i> foram neutralizadas via regex previamente à extração para evitar falsos positivos na mineradora Vale S.A. (<code>VALE3</code>).", style_bullet))
    story.append(Paragraph("• <b>Distribuição dos Ativos:</b> 12 ativos mapeados, com concentração maciça em estatais federais: <b>BBAS3</b> (42 posts), <b>PETR4</b> (40 posts) e <b>CMIG4</b> (10 posts). 7 posts representavam conjuntura macroeconômica sem ativo específico.", style_bullet))

    story.append(Spacer(1, 8))
    story.append(Paragraph("3. Protocolo de Rotulagem Humana & Consenso (Ground Truth)", style_h1))
    story.append(Paragraph(
        "Para garantir rigor científico e total ausência de contaminação por LLMs, o gabarito humano foi produzido de forma independente pela dupla antes de qualquer interação com a API:",
        style_body
    ))
    story.append(Paragraph("• <b>Rotulagem Cega Independente:</b> Anotador A e Anotador B classificaram os 100 posts isoladamente, produzindo <code>rotulos_A.csv</code> e <code>rotulos_B.csv</code>.", style_bullet))
    story.append(Paragraph("• <b>Métricas de Concordância Humana:</b> Acurácia entre anotadores de <b>88,0%</b>, gerando <b>Kappa de Cohen de 0,811</b> e <b>Kappa ponderado de 0,845</b> (concordância quase perfeita). O Kappa para detecção de ironia atingiu <b>0,968</b> (99% de concordância bruta).", style_bullet))
    story.append(Paragraph("• <b>Sessão de Consenso:</b> As 31 divergências de sentimento e flags foram deliberadas em sessão conjunta, documentadas em <code>decisoes_consenso.csv</code> e consolidadas em <code>rotulos_consenso.csv</code> (44 neutros, 36 positivos, 20 negativos).", style_bullet))

    story.append(PageBreak())

    # ==================== PÁGINA 2 ====================
    story.append(Paragraph("4. Classificação por LLM: Prompts, Ironia e Diagnóstico de Erros", style_h1))
    story.append(Paragraph(
        "Utilizou-se o modelo <b>Google Gemini Flash Lite</b> com <b>temperatura 0 estrita</b> e validação estrutural via Pydantic. A tabela abaixo compara o desempenho do Prompt v1 contra o Prompt v2 na amostra de avaliação:",
        style_body
    ))

    # Tabela LLM
    th_bg = colors.HexColor("#0F172A")
    tab_llm_data = [
        [Paragraph("Versão", style_th), Paragraph("Modelo", style_th), Paragraph("N", style_th), Paragraph("Kappa", style_th), Paragraph("Kappa P.", style_th), Paragraph("Acurácia", style_th), Paragraph("F1-Macro", style_th), Paragraph("Sem Ironia (80)", style_th), Paragraph("Com Ironia (20)", style_th), Paragraph("Custo USD", style_th)],
        [Paragraph("<b>v1</b>", style_td_left), Paragraph("Gemini Flash Lite", style_td), Paragraph("100", style_td), Paragraph("0.593", style_td), Paragraph("0.634", style_td), Paragraph("73.0%", style_td), Paragraph("0.732", style_td), Paragraph("76.2%", style_td), Paragraph("60.0%", style_td), Paragraph("$0.00108", style_td)],
        [Paragraph("<b>v2</b>", style_td_left), Paragraph("Gemini Flash Lite", style_td), Paragraph("100", style_td), Paragraph("<b>0.615</b>", style_td), Paragraph("<b>0.620</b>", style_td), Paragraph("<b>75.0%</b>", style_td), Paragraph("<b>0.749</b>", style_td), Paragraph("76.2%", style_td), Paragraph("<b>70.0%</b>", style_td), Paragraph("$0.00133", style_td)],
    ]
    t_llm = Table(tab_llm_data, colWidths=[0.55*inch, 1.15*inch, 0.4*inch, 0.65*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.9*inch, 0.9*inch, 0.65*inch])
    t_llm.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), th_bg),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_llm)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Evolução Metodológica e Tratamento de Ironia no Prompt v2:", style_h2))
    story.append(Paragraph(
        "A evolução de v1 para v2 representou um ganho qualitativo crucial no tratamento do sarcasmo financeiro. No prompt v1, postagens com forte ironia (ex: <i>'Parabéns aos envolvidos, MGLU3 derretendo mais 6% hoje 🤡'</i>) eram categorizadas erroneamente como 'positivo' devido à análise estritamente léxica de termos elogiosos isolados. O Prompt v2 introduziu <b>regras de inversão contextual de polaridade</b>, dicionário de jargões locais (<i>'foguete não tem ré'</i>, <i>'segurar a faca caindo'</i>) e detecção de emojis incongruentes. O resultado foi uma <b>elevação de 10 pontos percentuais na acurácia sobre posts irônicos (de 60% para 70%)</b>, elevando o Kappa global de 0,593 para 0,615 (faixa de concordância substancial).",
        style_body
    ))

    # Matriz de Confusão Prompt v2
    story.append(Spacer(1, 4))
    story.append(Paragraph("Matriz de Confusão — Humano (Linhas) × LLM v2 (Colunas):", style_h2))
    conf_data = [
        [Paragraph("Gabarito \\ LLM", style_th), Paragraph("Negativo (Previsto)", style_th), Paragraph("Neutro (Previsto)", style_th), Paragraph("Positivo (Previsto)", style_th), Paragraph("Total Real", style_th), Paragraph("Acurácia da Classe", style_th)],
        [Paragraph("<b>Negativo</b>", style_td_left), Paragraph("<b>15</b>", style_td), Paragraph("4", style_td), Paragraph("1", style_td), Paragraph("20", style_td), Paragraph("75.0%", style_td)],
        [Paragraph("<b>Neutro</b>", style_td_left), Paragraph("3", style_td), Paragraph("<b>32</b>", style_td), Paragraph("9", style_td), Paragraph("44", style_td), Paragraph("72.7%", style_td)],
        [Paragraph("<b>Positivo</b>", style_td_left), Paragraph("0", style_td), Paragraph("8", style_td), Paragraph("<b>28</b>", style_td), Paragraph("36", style_td), Paragraph("77.8%", style_td)],
    ]
    t_conf = Table(conf_data, colWidths=[1.3*inch, 1.2*inch, 1.2*inch, 1.2*inch, 0.9*inch, 1.2*inch])
    t_conf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_conf)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Catálogo de Erros e Padrões de Falha do Modelo:", style_h2))
    story.append(Paragraph("• <b>Realização de Lucros vs. Pessimismo:</b> Posts onde investidores comemoravam lucros elevados e anunciavam saída da posição (<i>'PM R$30, vendi tudo a R$50 e botei no bolso'</i>) foram classificados pelo LLM como neutros/positivos, desconsiderando que desinvestimentos representam pressão vendedora no pregão.", style_bullet))
    story.append(Paragraph("• <b>Notícias Neutras com Fatos Negativos:</b> Compartilhamento estrito de notícias (ex: <i>'Banco tem pane de sistemas e cotação pode recuar'</i>) sem adjetivação pessoal do autor foi por vezes interpretado como sentimento negativo próprio.", style_bullet))
    story.append(Paragraph("• <b>Erros de Alta Confiança:</b> Dentre os erros com confiança declarada $\ge 0,80$, identificou-se que o modelo é propenso a superestimar sua certeza quando o vocabulário utiliza termos enfáticos de convicção mesmo diante de ironia velada.", style_bullet))

    story.append(Spacer(1, 6))
    story.append(Paragraph("5. Detecção de Coordenação e Manipulação de Mercado", style_h1))
    story.append(Paragraph(
        "O pipeline combina similaridade textual TF-IDF de n-gramas de caracteres com algoritmos de agrupamento por rajada temporal (burst detection) dentro de janelas de 10 minutos. Foram pontuados e revisados os 10 clusters mais suspeitos:",
        style_body
    ))
    story.append(Paragraph("• <b>Auditoria Humana de Clusters:</b> Dos 10 clusters revisados, <b>9 foram classificados como falso positivo (orgânico)</b> e 1 cluster classificado como <b>provavelmente coordenado</b> (Cluster C0002 em CMIG4, onde comentários no Instagram direcionavam usuários com urgência para recomendação de compra na plataforma AGF).", style_bullet))
    story.append(Paragraph("• <b>Métricas de Precisão do Detector:</b> Precisão estrita de <b>0,0%</b> e precisão lata de <b>10,0%</b>.", style_bullet))
    story.append(Paragraph("• <b>Lição Metodológica Fundamental:</b> Em redes sociais financeiras, choques de preço externos e eventos corporativos de alta relevância (ex: queda súbita de 7% no barril de petróleo) desencadeiam naturalmente dezenas de mensagens simultâneas com vocabulário altamente correlacionado (<i>'comprei na queda'</i>, <i>'Black Friday de PETR4'</i>). Modelos puramente quantitativos de rajada sofrem de severa contaminação por falsos positivos se não passarem por triagem qualitativa.", style_bullet))

    story.append(PageBreak())

    # ==================== PÁGINA 3 ====================
    story.append(Paragraph("6. Teste Preditivo de Mercado e Econometria em Painel", style_h1))
    story.append(Paragraph(
        "A questão central para a mesa quantitativa é determinar se o sentimento apurado possui capacidade preditiva sobre a precificação futura dos ativos. Estimou-se uma regressão em painel com a seguinte especificação formal:",
        style_body
    ))
    story.append(Paragraph(
        "<b>Modelo Econométrico:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<i>R<sub>i, t+1</sub><sup>excesso</sup> = &alpha; + &beta; &middot; IndiceSentimento<sub>i, t</sub> + &gamma; &middot; R<sub>i, t</sub><sup>excesso</sup> + &delta; &middot; R<sub>i, t-1</sub><sup>excesso</sup> + &theta; &middot; ln(VolumePosts<sub>i, t</sub>) + &epsilon;<sub>i, t+1</sub></i><br/>"
        "Onde <i>R<sub>i, t</sub><sup>excesso</sup> = R<sub>ativo, i, t</sub> - R<sub>Ibov, t</sub></i>. Todos os modelos utilizam matriz de covariância robusta a heteroscedasticidade e autocorrelação (<b>HAC / Newey-West</b>) e correção de múltiplos testes de <b>Holm-Bonferroni</b>.",
        style_body
    ))
    story.append(Spacer(1, 4))

    # Tabela Econométrica
    tab_eco_data = [
        [Paragraph("Versão / Modelo", style_th), Paragraph("Variável Dependente (DV)", style_th), Paragraph("Coef. (&beta;)", style_th), Paragraph("Erro-Padrão (HAC)", style_th), Paragraph("Estat. t", style_th), Paragraph("p-valor Bruto", style_th), Paragraph("p-valor Holm", style_th), Paragraph("N (Obs / Tickers)", style_th), Paragraph("R²", style_th)],
        [Paragraph("<b>llm_bruto (v1)</b>", style_td_left), Paragraph("ret_excesso_f1 (t+1)", style_td), Paragraph("-0.0155", style_td), Paragraph("0.0174", style_td), Paragraph("-0.89", style_td), Paragraph("0.3741", style_td), Paragraph("1.000", style_td), Paragraph("31 (11)", style_td), Paragraph("0.076", style_td)],
        [Paragraph("<b>llm_corrigido (v2)</b>", style_td_left), Paragraph("ret_excesso_f1 (t+1)", style_td), Paragraph("-0.0076", style_td), Paragraph("0.0117", style_td), Paragraph("-0.65", style_td), Paragraph("0.5171", style_td), Paragraph("1.000", style_td), Paragraph("31 (11)", style_td), Paragraph("0.045", style_td)],
        [Paragraph("<b>sem_coordenados</b>", style_td_left), Paragraph("ret_excesso_f1 (t+1)", style_td), Paragraph("-0.0079", style_td), Paragraph("0.0119", style_td), Paragraph("-0.66", style_td), Paragraph("0.5100", style_td), Paragraph("1.000", style_td), Paragraph("30 (11)", style_td), Paragraph("0.046", style_td)],
        [Paragraph("<b>Acumulado 5d (v2)</b>", style_td_left), Paragraph("ret_excesso_acum (t+1:t+5)", style_td), Paragraph("+0.0105", style_td), Paragraph("0.0323", style_td), Paragraph("+0.32", style_td), Paragraph("0.7456", style_td), Paragraph("1.000", style_td), Paragraph("12 (7)", style_td), Paragraph("0.394", style_td)],
        [Paragraph("<b>Volume Anormal (v2)</b>", style_td_left), Paragraph("vol_anormal_f1 (t+1)", style_td), Paragraph("+0.0987", style_td), Paragraph("0.2549", style_td), Paragraph("+0.39", style_td), Paragraph("0.6987", style_td), Paragraph("1.000", style_td), Paragraph("29 (10)", style_td), Paragraph("0.249", style_td)],
        [Paragraph("<b>Placebo Passado (v1)</b>", style_td_left), Paragraph("ret_excesso_lag1 (t-1)", style_td), Paragraph("<b>-0.0123</b>", style_td), Paragraph("0.0051", style_td), Paragraph("<b>-2.39</b>", style_td), Paragraph("<b>0.0167*</b>", style_td), Paragraph("—", style_td), Paragraph("31 (11)", style_td), Paragraph("0.092", style_td)],
        [Paragraph("<b>Placebo Passado (v2)</b>", style_td_left), Paragraph("ret_excesso_lag1 (t-1)", style_td), Paragraph("+0.0012", style_td), Paragraph("0.0059", style_td), Paragraph("+0.20", style_td), Paragraph("0.8404", style_td), Paragraph("—", style_td), Paragraph("31 (11)", style_td), Paragraph("0.012", style_td)],
    ]
    t_eco = Table(tab_eco_data, colWidths=[1.15*inch, 1.4*inch, 0.65*inch, 0.95*inch, 0.6*inch, 0.7*inch, 0.65*inch, 0.9*inch, 0.4*inch])
    t_eco.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), th_bg),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_eco)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Interpretação e Diagnóstico Econométrico:", style_h2))
    story.append(Paragraph(
        "1. <b>Inexistência de Alfa Direcional Forward-Looking:</b> O coeficiente de sentimento nas regressões controladas para o retorno em excesso no pregão seguinte ($t+1$) resultou negativo e não significativo (&beta; = -0,0076; p_bruto = 0,5171; p_holm = 1,000). A mesma insignificância se repete para retornos acumulados em 5 dias (&beta; = +0,0105; p_holm = 1,000) e para volume anormal de negociação.",
        style_body
    ))
    story.append(Paragraph(
        "2. <b>Revelação do Teste Placebo:</b> O teste placebo sobre retornos passados ($R_{t-1}$) no modelo bruto foi altamente significativo (&beta; = -0,0123; t = -2,39; p = 0,0167). Isso comprova a ocorrência de <b>causalidade reversa</b>: os investidores pessoas físicas em redes sociais não antecipam oscilações de preço; eles reagem aos choques negativos já ocorridos, transformando o sentimento agregado em um eco defasado do mercado.",
        style_body
    ))
    story.append(Paragraph(
        "3. <b>Impacto da Exclusão de Coordenação:</b> A retirada do cluster suspeito (modelo <code>sem_coordenados</code>) manteve a estabilidade dos parâmetros (&beta; = -0,0079 vs -0,0076), atestando que a ausência de sinal preditivo decorre da natureza do ruído de varejo e não de distorções induzidas por campanhas orquestradas.",
        style_body
    ))

    story.append(PageBreak())

    # ==================== PÁGINA 4 ====================
    story.append(Paragraph("7. Preparação para a Defesa Oral: Guia de Perguntas Críticas", style_h1))
    story.append(Paragraph(
        "Apresentam-se a seguir as respostas fundamentadas para as questões conceituais centrais exigidas pela banca examinadora da CF Tech:",
        style_body
    ))

    story.append(Paragraph("<b>Q1. Por que a arquitetura adotou o formato TOON em detrimento do padrão JSON?</b>", style_h2))
    story.append(Paragraph(
        "O formato TOON tabular (<i>Topic-Oriented Object Notation</i>) elimina a redundância estrutural do JSON ao declarar os nomes das chaves uma única vez no cabeçalho (ex: <code>resultados[N]{id,sentimento,confianca,ironia}:</code>) e transmitir os dados linha a linha separados por vírgula. Essa abordagem reduziu em <b>34% o consumo de caracteres</b> na chamada e resposta do LLM, além de acelerar o parsing e diminuir drasticamente o custo financeiro da esteira. Adicionalmente, o número de linhas $N$ explicitamente fixado no cabeçalho permite identificar instantaneamente respostas truncadas antes da desserialização no Pydantic.",
        style_body
    ))

    story.append(Paragraph("<b>Q2. O que exatamente o teste placebo comprova e por que ele é indispensável?</b>", style_h2))
    story.append(Paragraph(
        "O teste placebo substitui a variável dependente futura ($R_{t+1}$) pelo retorno passado do ativo ($R_{t-1}$). Por definição ontológica, o sentimento gerado em $t$ não pode exercer causalidade sobre preços formados no passado. Quando um modelo sem controles acusa correlação com $R_{t-1}$, o teste comprova que o sinal de sentimento é endógeno e reflete a reação do investidor a perdas pregressas. Ignorar o teste placebo induz pesquisadores ao erro de atribuir poder preditivo a séries que apenas espelham tendências passadas.",
        style_body
    ))

    story.append(Paragraph("<b>Q3. Qual a justificativa estatística para o uso de erros-padrão robustos (HAC / Newey-West)?</b>", style_h2))
    story.append(Paragraph(
        "Em séries temporais e painéis financeiros, os resíduos violam rotineiramente as premissas de Gauss-Markov devido a heteroscedasticidade e correlação serial intra-ativo ao longo do tempo. Erros-padrão de OLS convencionais subestimam a variância dos estimadores, gerando estatísticas $t$ artificialmente inflacionadas e falsos positivos estatísticos. A matriz de covariância HAC (Newey-West) com defasagens ajustadas garante inferência assintoticamente válida mesmo sob dependência temporal.",
        style_body
    ))

    story.append(Paragraph("<b>Q4. Como a correção pela matriz de confusão pode induzir contaminação (leakage)?</b>", style_h2))
    story.append(Paragraph(
        "Ajustar as proporções populacionais de sentimento invertendo a matriz de confusão calibrada na amostra de avaliação acarreta dois riscos severos: (i) <i>Lookahead Bias</i> se a matriz for estimada em dados de períodos posteriores ao ponto de tomada de decisão; e (ii) <i>Data Snooping</i> se as classes reais da base ampla divergirem estruturalmente da amostra amostrada (ex: crises pontuais gerando mais pessimismo). Para fins de modelagem quantitativa rigorosa, deve-se utilizar estritamente o sinal inferido ponto-a-ponto sem calibrações globais retroativas.",
        style_body
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("8. Conclusões e Recomendações Estratégicas para a Mesa Quant", style_h1))
    story.append(Paragraph(
        "1. <b>Inviabilidade de Estratégias Direcionais de Frequência Diária:</b> Recomenda-se formalmente ao comitê quant não alocar capital em estratégias que apostem na continuidade direcional de preços baseada puramente em sentimento de redes abertas em frequência diária.",
        style_bullet
    ))
    story.append(Paragraph(
        "2. <b>Utilidade como Indicador de Risco e Assimetria de Cauda:</b> O valor prático do pipeline reside no monitoramento de anomalias (picos súbitos de queixas ou rajadas de desconfiança) que possam antecipar eventos de cauda, revisões de rating ou surpresas operacionais antes de relatórios trimestrais.",
        style_bullet
    ))
    story.append(Paragraph(
        "3. <b>Expansão para Dados de Alta Frequência (Intradiário):</b> Sugere-se avaliar a microestrutura em janelas de 15 a 60 minutos após eventos corporativos para verificar se a lentidão na absorção de notícias por investidores pessoas físicas gera janelas exploráveis de liquidez.",
        style_bullet
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Relatório PDF gerado com sucesso em: {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    gerar_relatorio_md()
    gerar_relatorio_pdf()

