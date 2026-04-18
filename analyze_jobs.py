import asyncio
from app.core.database import async_session
from app.services.vacancy_service import VacancyService
from app.services.ai_service import AIService

async def start_analysis(user_skills=""):
    ai_service = AIService(user_skills=user_skills)
    print(f"🧠 AI analysis started with skills: {user_skills if user_skills else 'Default Profile'}")

    async with async_session() as session:
        v_service = VacancyService(session)

        jobs = await v_service.get_unanalyzed_vacancies()
        print(f"Found {len(jobs)} vacancies for analysis.")

        for job in jobs:
            print(f"Analyzing: {job.title}...")

            ai_result = await ai_service.analyze_vacancy(job.description)
            if ai_result:
                await v_service.update_vacancy_ai_data(job.id, ai_result)
                print(f"✅ Done. Score: {ai_result.get('score')}%")
            else:
                print(f"❌ Analysis error for ID {job.id}")

            await asyncio.sleep(5)

    print("🚀 All vacancies processed!")

if __name__ == "__main__":
    asyncio.run(start_analysis())