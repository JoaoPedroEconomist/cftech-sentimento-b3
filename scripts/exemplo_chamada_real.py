import os
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from src import config, llm, toon

# Let's inspect prompt v1
system, user_tpl, h = llm.carregar_prompt("v1")
print(f"Loaded prompt v1 (hash: {h})")

# Sample posts from real investor context (B3)
posts_amostra = [
    {"id": "1", "texto": "PETR4 bateu novo recorde de produção, resultado veio muito forte acima do esperado!"},
    {"id": "2", "texto": "Mais um dia maravilhoso vendo MGLU3 cair 6%, parabéns aos envolvidos 🤡"},
    {"id": "3", "texto": "Alguém sabe quando sai o balanço da VALE3?"},
]

user_content = llm.montar_user(user_tpl, posts_amostra)
print("\n--- User content sent ---")
print(user_content)

from google import genai
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

prompt_input = f"{system}\n\n{user_content}"
print("\nCalling Gemini (gemini-3.8-flash)...")

interaction = client.interactions.create(
    model="gemini-3.8-flash",
    input=prompt_input,
)

texto = interaction.output_text
print("\n--- Raw Response from Gemini ---")
print(texto)

# Parse response
resultados = llm.parse_resposta(texto)
print(f"\n--- Successfully Parsed {len(resultados)} Resultados ---")
for r in resultados:
    print(f"ID: {r.id} | Sentimento: {r.sentimento} | Confiança: {r.confianca} | Ironia: {r.ironia} | Justificativa: {r.justificativa_curta}")
