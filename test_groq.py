from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(__file__), ".env")
)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {"role": "user", "content": "Hello! Are you working?"}
    ]
)

print(response.choices[0].message.content)