import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()


class AIService:
    def __init__(self, user_skills: str = None):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

        if user_skills and user_skills.strip():
            self.current_profile = f"User Skills and Experience: {user_skills}"
        else:
            self.current_profile = """
            Experience: Frontend Developer, System Administrator.
            Learning: Python (FastAPI, Scraping), English (upper-intermediate).
            Goal: Junior Python Developer.
            """

    async def analyze_vacancy(self, description: str):
        prompt = f"""
        Act as a professional IT recruiter. 
        Analyze the following job vacancy based on the Candidate Profile provided below.

        Candidate Profile:
        {self.current_profile}

        Vacancy Description:
        {description}

        Return ONLY a JSON object (no markdown, no explanations) with:
        1. "score": int (0-100, where 100 is a perfect match for the skills mentioned)
        2. "tech_stack": list of strings (key technologies mentioned in the vacancy)
        3. "summary": string (brief 2-sentence feedback explaining the score in English)
        """

        try:
            response = self.model.generate_content(prompt)
            text_content = response.text.strip()
            if text_content.startswith("```json"):
                text_content = text_content[7:-3].strip()
            elif text_content.startswith("```"):
                text_content = text_content[3:-3].strip()

            return json.loads(text_content)
        except Exception as e:
            print(f"AI Analysis Error: {e}")
            return None