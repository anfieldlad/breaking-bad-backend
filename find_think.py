import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

print("Searching for models with 'think'...")
found = False
for m in client.models.list():
    if "think" in m.name.lower():
        print(f"FOUND: {m.name}")
        found = True
if not found:
    print("No model with 'think' in the name was found.")
    print("Showing 2.0-flash models instead:")
    for m in client.models.list():
        if "2.0-flash" in m.name:
            print(f"FLASH: {m.name}")
