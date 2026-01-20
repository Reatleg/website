from ai_analyzer import FuryTraderAI
from dotenv import load_dotenv
import os

load_dotenv()

ai = FuryTraderAI(api_key=os.getenv('OPENAI_API_KEY'))
print("✅ AI Analyzer initialized successfully!")