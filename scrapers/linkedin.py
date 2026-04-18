import asyncio
from playwright.async_api import async_playwright
from app.schemas.vacancy import VacancyCreate
from app.schemas.enums import JobSource


class LinkedInScraper:
    def __init__(self, keyword="Python"):
        self.keyword = keyword
        self.url = f"https://www.linkedin.com/jobs/search/?keywords={self.keyword}&location=Ukraine"

    async def scrape(self) -> list[VacancyCreate]:
        async with async_playwright() as p:
            print(f"🔗 [LinkedIn] Starting headless browser for: {self.keyword}...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            try:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)

                await page.wait_for_selector(".jobs-search__results-list", timeout=15000)
            except Exception as e:
                print(f"❌ LinkedIn blocking or timeout: {e}")
                await browser.close()
                return []

            vacancies = []
            items = await page.query_selector_all(".jobs-search__results-list li")

            for item in items[:15]:
                try:
                    title_elem = await item.query_selector(".base-search-card__title")
                    company_elem = await item.query_selector(".base-search-card__subtitle")
                    link_elem = await item.query_selector(".base-card__full-link")

                    if title_elem and link_elem:
                        title = await title_elem.inner_text()
                        company = await company_elem.inner_text() if company_elem else "Unknown"
                        url = await link_elem.get_attribute("href")

                        vacancies.append(VacancyCreate(
                            title=title.strip(),
                            company=company.strip(),
                            url=url.split("?")[0],
                            description=f"LinkedIn vacancy for {self.keyword}. (Full text parsing required for AI)",
                            source=JobSource.LINKEDIN,
                            salary=None
                        ))
                        print(f"✅ LinkedIn parsed: {title.strip()}")
                except Exception as e:
                    print(f"⚠️ Error parsing LinkedIn item: {e}")

            await browser.close()
            return vacancies

    async def get_full_description(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=60000)
                description = await page.locator(".description__text").inner_text()
                await browser.close()
                return description
            except:
                await browser.close()
                return ""