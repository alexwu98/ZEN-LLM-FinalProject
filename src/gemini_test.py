import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="models/gemini-2.0-flash",
    contents="Write a one-sentence bedtime story about a unicorn."
)

print(response.text)
