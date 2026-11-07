"""Configuração central: caminhos, schema e parâmetros fixos (registrados em docs/decisoes.md)."""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATA_RAW = RAIZ / "data" / "raw"
DATA_PROC = RAIZ / "data" / "processed"
DATA_CACHE = RAIZ / "data" / "cache"
PROMPTS = RAIZ / "prompts"
REPORTS = RAIZ / "reports"

# Arquivos
POSTS_RAW_CANDIDATOS = ["posts.parquet", "posts.csv"]
AMOSTRA_AVALIACAO = DATA_RAW / "amostra_avaliacao.csv"  # fornecida pela CF Tech (100 posts, coluna id)
POSTS_PARQUET = DATA_PROC / "posts.parquet"
LLM_PARQUET = DATA_PROC / "sentimento_llm.parquet"
CLUSTERS_CSV = DATA_PROC / "clusters_suspeitos.csv"
CLUSTERS_REVISADOS_CSV = DATA_PROC / "clusters_revisados.csv"

# Schema mínimo da base
COLUNAS_OBRIGATORIAS = ["id", "data_hora", "autor_id", "plataforma", "texto"]

# Rótulos
SENTIMENTOS = ["negativo", "neutro", "positivo"]
FLAGS = ["ironia", "giria_meme", "suspeita_coordenacao", "irrelevante"]

# Horário de mercado (B3). Posts após o corte contam para o próximo pregão.
TZ_LOCAL = "America/Sao_Paulo"
HORA_CORTE = 17  # 17:00 BRT (parametrizável nos testes de robustez)

# Extração de tickers (B3): 4 letras + 1-2 dígitos, aceitando maiúsculas e minúsculas, além do fracionário (ex: petr4, PETR4F)
REGEX_TICKER = r"\b([A-Za-z]{4}\d{1,2}[Ff]?)\b"
# Palavras de 4 letras + dígito que NÃO são tickers (ampliar durante a exploração)
STOPLIST_TICKERS = {"COVID19", "WIN10", "FIFA22", "FIFA23", "FIFA24", "FIFA25", "FIFA26", "COP26", "COP27", "COP28"}

# Mapa nome de empresa -> ticker (ampliar com a base real). Chaves em minúsculas, sem acento.
NOMES_EMPRESAS = {
    "petrobras": "PETR4",
    "vale": "VALE3",
    "itau": "ITUB4",
    "bradesco": "BBDC4",
    "banco do brasil": "BBAS3",
    "ambev": "ABEV3",
    "magalu": "MGLU3",
    "magazine luiza": "MGLU3",
    "weg": "WEGE3",
    "americanas": "AMER3",
    "eletrobras": "ELET3",
}
# Nomes que também são palavras comuns: exigem contexto financeiro para valer como menção
NOMES_AMBIGUOS = {"vale", "weg"}
PALAVRAS_CONTEXTO_FINANCEIRO = {
    "acao", "acoes", "papel", "papeis", "bolsa", "b3", "dividendo", "dividendos", "balanco",
    "comprar", "vender", "compra", "venda", "alta", "queda", "cotacao", "preco", "ticker", "lucro",
}

# Rotulagem / avaliação
N_AMOSTRA = 100
SEED = 42

# Coordenação
LIMIAR_COSSENO = 0.80
JANELA_RAJADA_MIN = 10
MIN_AUTORES_RAJADA = 3
MIN_POSTS_AUTOR_HISTORICO = 5  # abaixo disso o autor conta como "pouco histórico"
N_CLUSTERS_REVISAO = 30
PESOS_SUSPEITA = {
    "similaridade": 0.35,
    "rajada": 0.25,
    "autor_novo": 0.15,
    "baixa_liquidez": 0.10,
    "urgencia_alvo": 0.15,
}
URGENCIA_REGEX = (
    r"(entra(m)? (agora|ja)|corre(m)?\b|ultima chance|antes que (acabe|suba|decole)|"
    r"vai (a|para|pra) r?\$ ?\d|alvo( de preco)?:? ?r?\$ ?\d|nao fiquem de fora|garantido|certeza que vai)"
)

# Teste preditivo
N_MIN_POSTS = 3
JANELA_VOL_ANORMAL = 20
HAC_LAGS = 5
ALFA = 0.05

# LLM
LLM_MODEL_PADRAO = "gemini-3.1-flash-lite"
LLM_BATCH = 20
LLM_MAX_RETRIES = 3
