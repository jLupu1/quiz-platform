from dotenv import load_dotenv
from google import genai
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents="Given the question - What is phishing? - What would you grade the answer out of 5 provided by a student - Phishing is a sort of social engineering cyberattack aimed at stealing personal information. "
)
print(response.text)