import os
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
print(f"API key loaded: {api_key[:6]}... (length: {len(api_key)})", flush=True)

client = genai.Client(api_key=api_key)

try:
    print("Testing client.interactions.create with gemini-3.8-flash...", flush=True)
    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input="Diga 'Conexão realizada com sucesso!' em português.",
    )
    print("Output text:", interaction.output_text, flush=True)
    if hasattr(interaction, "usage"):
        print("Usage:", interaction.usage, flush=True)
except Exception as e:
    print("Error:", type(e), e, flush=True)
