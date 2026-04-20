import asyncio
import logging
from app.core.database import async_session
from app.services.vacancy_service import VacancyService
from scrapers.djinni import DjinniScraper
from scrapers.dou import DOUScraper
from scrapers.linkedin import LinkedInScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_all_scrapers(keyword="Python", exp="no", selected_sources=None):
    if selected_sources is None:
        selected_sources = ["djinni", "dou", "linkedin"]

    scrapers = []
    if "djinni" in selected_sources:
        scrapers.append(DjinniScraper(keyword=keyword, exp_level=exp))
    if "dou" in selected_sources:
        scrapers.append(DOUScraper(keyword=keyword, exp=exp))
    if "linkedin" in selected_sources:
        scrapers.append(LinkedInScraper(keyword=keyword))

    all_jobs = []

    # ❗️ ЗАПУСКАЕМ ПО ОЧЕРЕДИ, чтобы браузеры не конфликтовали
    for scraper in scrapers:
        name = scraper.__class__.__name__
        logger.info("🚀 Starting %s...", name)
        try:
            res = await scraper.scrape()
            if isinstance(res, list):
                logger.info("✅ [%s] Found %d vacancies.", name, len(res))
                all_jobs.extend(res)
            else:
                logger.warning("⚠️ [%s] Returned non-list result: %s", name, res)
        except Exception as e:
            # Теперь, если Playwright упадет, мы точно увидим почему
            logger.error("❌ [%s] Scraper failed with error: %s", name, e, exc_info=True)

    async with async_session() as session:
        service = VacancyService(session)
        new_count = await service.bulk_create_vacancies(all_jobs)
        logger.info("Total new vacancies added: %d", new_count)

if __name__ == "__main__":
    asyncio.run(run_all_scrapers())