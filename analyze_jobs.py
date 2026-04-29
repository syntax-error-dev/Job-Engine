import asyncio
import logging
from app.core.database import async_session
from app.services.vacancy_service import VacancyService
from app.services.ai_service import AIService, REQUEST_DELAY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONCURRENCY_LIMIT = 1
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)


async def process_job(job, ai_service, v_service):
    async with semaphore:
        logger.info("Analyzing: %s", job.title)
        ai_result = await ai_service.analyze_vacancy(job.description)
        if ai_result:
            await v_service.update_vacancy_ai_data(job.id, ai_result)
        else:
            logger.warning("Skipped (no result): %s", job.title)
        await asyncio.sleep(REQUEST_DELAY)


async def start_analysis(user_skills=""):
    ai_service = AIService(user_skills=user_skills)
    logger.info("AI analysis started")

    async with async_session() as session:
        v_service = VacancyService(session)
        jobs = await v_service.get_unanalyzed_vacancies()
        logger.info("Found %d vacancies for analysis.", len(jobs))

        if not jobs:
            return

        logger.info(
            "Estimated time: ~%d minutes for %d vacancies (free tier, %ds delay)",
            (len(jobs) * REQUEST_DELAY) // 60 + 1,
            len(jobs),
            REQUEST_DELAY,
        )

        tasks = [process_job(job, ai_service, v_service) for job in jobs]
        await asyncio.gather(*tasks)

    logger.info("✅ All vacancies processed!")


if __name__ == "__main__":
    asyncio.run(start_analysis())