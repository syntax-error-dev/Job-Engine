import asyncio
import json
import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


# Строгая схема ответа для Gemini
class VacancyAnalysis(BaseModel):
    score: int = Field(description="0-100, where 100 is a perfect match for the candidate's skills")
    tech_stack: list[str] = Field(description="key technologies mentioned in the vacancy")
    summary: str = Field(description="brief 2-sentence feedback explaining the score in English")


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

        models_to_try = ["gemini-3.1-flash-lite-preview"]
        max_retries = 5

        for model_name in models_to_try:
            for attempt in range(max_retries):
                try:
                    # ИСПОЛЬЗУЕМ АСИНХРОННЫЙ КЛИЕНТ (.aio) И ЖДЕМ (await)
                    response = await self.client.aio.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=VacancyAnalysis,  # Заставляем вернуть четкий JSON
                            temperature=0.1,  # Делаем ответы менее креативными и более стабильными
                        ),
                    )

                    # Парсинг теперь безопасен на 100%
                    result = json.loads(response.text.strip())

                    # Финальная нормализация
                    result["score"] = max(0, min(100, int(result.get("score", 0))))
                    return result

                except Exception as e:
                    err_str = str(e)
                    # Обработка лимитов API
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        match = re.search(r'retry[^\d]*(\d+)', err_str, re.IGNORECASE)
                        wait = int(match.group(1)) + 3 if match else 30

                        if attempt < max_retries - 1:
                            print(
                                f"⏳ [{model_name}] Rate limit, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                            await asyncio.sleep(wait)
                        else:
                            print(f"⚠️ [{model_name}] Rate limit after {max_retries} attempts, trying next model...")
                            break
                    else:
                        print(f"❌ AI Analysis Error ({model_name}): {e}")
                        # При другой ошибке пробуем следующую модель
                        break

        print("❌ All models exhausted, skipping vacancy.")
        return None