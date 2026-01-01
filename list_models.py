import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

print("Listing models containing 'think' or 'flash'...")
models = list(client.models.list())
for m in models:
    if "flash" in m.name.lower() or "think" in m.name.lower():
        print(f"Model ID: {m.name}")
print(f"Total models: {len(models)}")
