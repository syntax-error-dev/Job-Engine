import asyncio
import json
import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class VacancyAnalysis(BaseModel):
    score: int = Field(description="0-100, where 100 is a perfect match for the candidate's skills")
    tech_stack: list[str] = Field(description="key technologies mentioned in the vacancy")
    summary: str = Field(description="brief 2-sentence feedback explaining the score in English")


FALLBACK_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

REQUEST_DELAY = 10


class AIService:
    def __init__(self, user_skills: str = None):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        if user_skills and user_skills.strip():
            self.current_profile = f"User Skills and Experience: {user_skills}"
        else:
            self.current_profile = """
            Experience: Frontend Developer, System Administrator.
            Learning: Python (FastAPI, Scraping), English (upper-intermediate).
            Goal: Senior Python Developer.
            """

    async def analyze_vacancy(self, description: str) -> dict | None:
        prompt = f"""
        Act as a professional IT recruiter.
        Analyze the following job vacancy based on the Candidate Profile provided below.

        Candidate Profile:
        {self.current_profile}

        Vacancy Description:
        {description}
        """

        for model_name in FALLBACK_MODELS:
            result = await self._try_model(model_name, prompt)
            if result is not None:
                return result
            print(f"⏭️ Switching to next fallback model...")

        print("❌ All models exhausted, skipping vacancy.")
        return None

    async def _try_model(self, model_name: str, prompt: str) -> dict | None:
        max_retries = 4

        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=VacancyAnalysis,
                        temperature=0.1,
                    ),
                )

                result = json.loads(response.text.strip())
                result["score"] = max(0, min(100, int(result.get("score", 0))))
                print(f"✅ [{model_name}] Analysis done (score: {result['score']})")
                return result

            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                is_overloaded  = "503" in err_str or "UNAVAILABLE" in err_str

                if is_rate_limit:
                    match = re.search(r'retry[^\d]*(\d+)', err_str, re.IGNORECASE)
                    api_wait    = int(match.group(1)) + 3 if match else None
                    backoff_wait = 30 * (attempt + 1)   # 30 / 60 / 90 / 120 сек
                    wait = api_wait if api_wait else backoff_wait
                    if attempt < max_retries - 1:
                        print(f"⏳ [{model_name}] Rate limit, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait)
                    else:
                        print(f"⚠️ [{model_name}] Rate limit after {max_retries} attempts → try next model.")
                        return None

                elif is_overloaded:
                    print(f"⚠️ [{model_name}] Service overloaded (503) → try next model.")
                    return None

                else:
                    if attempt < 1:
                        print(f"⚠️ [{model_name}] Unexpected error, retrying once: {e}")
                        await asyncio.sleep(5)
                    else:
                        print(f"❌ [{model_name}] Fatal error → try next model: {e}")
                        return None

        return None