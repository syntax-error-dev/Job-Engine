import asyncio
import json
import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


class AIService:
    def __init__(self, user_skills: str = None):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        if user_skills and user_skills.strip():
            self.current_profile = f"User Skills and Experience: {user_skills}"
        else:
            self.current_profile = """
            Experience: Frontend Developer, System Administrator.
            Learning: Python (FastAPI, Scraping), English (upper-intermediate).
            Goal: Junior Python Developer.
            """

    async def analyze_vacancy(self, description: str) -> dict | None:
        prompt = f"""
        Act as a professional IT recruiter.
        Analyze the following job vacancy based on the Candidate Profile provided below.

        Candidate Profile:
        {self.current_profile}

        Vacancy Description:
        {description}

        Return ONLY a JSON object (no markdown, no explanations) with these exact keys:
        1. "score": int (0-100, where 100 is a perfect match for the candidate's skills)
        2. "tech_stack": list of strings (key technologies mentioned in the vacancy)
        3. "summary": string (brief 2-sentence feedback explaining the score in English)
        """

        models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash-8b"]
        max_retries = 3

        for model_name in models_to_try:
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        ),
                    )
                    text_content = response.text.strip()

                    if text_content.startswith("```json"):
                        text_content = text_content[7:].strip().rstrip("```").strip()
                    elif text_content.startswith("```"):
                        text_content = text_content[3:].strip().rstrip("```").strip()

                    result = json.loads(text_content)
                    result.setdefault("score", 0)
                    result.setdefault("tech_stack", [])
                    result.setdefault("summary", "No summary available.")
                    result["score"] = max(0, min(100, int(result["score"])))
                    return result

                except json.JSONDecodeError as e:
                    print(f"AI JSON Parse Error ({model_name}): {e}\nRaw: {text_content[:300]}")
                    return None

                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        match = re.search(r'retry[^\d]*(\d+)', err_str, re.IGNORECASE)
                        wait = int(match.group(1)) + 3 if match else 30

                        if attempt < max_retries - 1:
                            print(f"⏳ [{model_name}] Rate limit, waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                            await asyncio.sleep(wait)
                        else:
                            print(f"⚠️ [{model_name}] Rate limit after {max_retries} attempts, trying next model...")
                            break
                    else:
                        print(f"AI Analysis Error ({model_name}): {e}")
                        return None

        print("❌ All models exhausted, skipping vacancy.")
        return None