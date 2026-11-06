import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, llm

print("=" * 60)
print("TESTE REAL DO PIPELINE DE CLASSIFICAÇÃO COM LLM (GEMINI)")
print("=" * 60)

# 1. Verificação da chave da API
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERRO: Nenhuma chave de API encontrada no .env!")
    sys.exit(1)

masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***"
print(f"1. Chave carregada com sucesso do .env: {masked_key} (tamanho: {len(api_key)})")
print(f"   Modelo configurado: {os.getenv('LLM_MODEL', 'gemini-3.8-flash')}")

# 2. Dataset de teste real com casos representativos do investidor brasileiro na B3
posts_teste = pd.DataFrame([
    {
        "id": "101",
        "texto": "PETR4 bateu novo recorde histórico de produção no pré-sal! Dividendos devem vir estratosféricos esse trimestre 🚀",
    },
    {
        "id": "102",
        "texto": "Mais um dia maravilhoso vendo MGLU3 derreter 7% na abertura. Parabéns aos gênios envolvidos 🤡",
    },
    {
        "id": "103",
        "texto": "Alguém sabe dizer em que data sai a divulgação dos resultados do 3T26 da VALE3?",
    },
    {
        "id": "104",
        "texto": "Depois de analisar o balanço e a dívida da WEGE3, decidi zerar minha posição. Risco/retorno não compensa.",
    },
    {
        "id": "105",
        "texto": "Comprem agora antes que acabe! Papel vai a R$ 100 amanhã, lua garantida! 🚀🚀🚀",
    },
])

print(f"\n2. Submetendo lote de {len(posts_teste)} posts para classificação (versão v1)...")
for idx, r in posts_teste.iterrows():
    print(f"   [{r['id']}] {r['texto']}")

# 3. Execução real chamando llm.classificar
resultados, info = llm.classificar(
    posts=posts_teste,
    versao="v1",
    modelo=os.getenv("LLM_MODEL", "gemini-3.8-flash"),
    batch=10,
)

print("\n" + "=" * 60)
print("3. RESULTADOS DA CLASSIFICAÇÃO (PARSED & VALIDATED)")
print("=" * 60)
for idx, r in resultados.iterrows():
    ironia_flag = " [IRONIA DETECTADA!]" if r.get("ironia") else ""
    print(f"\nPost ID: {r['id']}")
    print(f"  Sentimento   : {r['sentimento'].upper()}")
    print(f"  Confiança    : {r['confianca'] * 100:.1f}%")
    print(f"  Ironia       : {r['ironia']}{ironia_flag}")
    print(f"  Justificativa: {r['justificativa_curta']}")

print("\n" + "=" * 60)
print("4. MÉTRICAS E CUSTO DA EXECUÇÃO")
print("=" * 60)
print(f"  Total de posts       : {info['total']}")
print(f"  Chamadas realizadas  : {info['chamadas']}")
print(f"  Posts em cache       : {info['em_cache']}")
print(f"  Tokens In (Prompt)   : {info['tokens_in']}")
print(f"  Tokens Out (Resp.)   : {info['tokens_out']}")
if info.get("custo_usd") is not None:
    print(f"  Custo estimado (USD) : ${info['custo_usd']:.6f}")
print(f"  Falhas               : {len(info['falhas'])}")

# 4. Teste de cache (executar novamente os mesmos posts não deve gerar novas chamadas)
print("\n" + "=" * 60)
print("5. TESTE DE CACHE")
print("=" * 60)
resultados_cache, info_cache = llm.classificar(
    posts=posts_teste,
    versao="v1",
    modelo=os.getenv("LLM_MODEL", "gemini-3.8-flash"),
    batch=10,
)
print(f"  Chamadas adicionais  : {info_cache['chamadas']}")
print(f"  Posts lidos do cache : {info_cache['em_cache']} de {info_cache['total']}")
assert info_cache["chamadas"] == 0, "Deveria ter recuperado 100% do cache sem novas chamadas à API!"
print("  -> Verificação de integridade do cache: SUCESSO!")

print("\n" + "=" * 60)
print("TESTE REAL CONCLUÍDO COM 100% DE SUCESSO!")
print("=" * 60)
