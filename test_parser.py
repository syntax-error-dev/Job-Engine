import asyncio
from app.core.database import async_session
from app.services.vacancy_service import VacancyService

from scrapers.djinni import DjinniScraper
from scrapers.dou import DOUScraper
from scrapers.linkedin import LinkedInScraper


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

    async with async_session() as session:
        service = VacancyService(session)

        for scraper in scrapers:
            name = scraper.__class__.__name__
            print(f"🕵️ Running {name}...")

            try:
                jobs = await scraper.scrape()
                print(f"[{name}] Found {len(jobs)} vacancies.")

                new_count = 0
                for job in jobs:
                    res = await service.create_vacancy(job)
                    if res:
                        new_count += 1
                print(f"✅ {name} done. Added {new_count} new vacancies.")
            except Exception as e:
                print(f"❌ Error in {name}: {e}")


if __name__ == "__main__":
    asyncio.run(run_all_scrapers())