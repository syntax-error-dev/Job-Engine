import asyncio
from playwright.async_api import async_playwright
from app.schemas.vacancy import VacancyCreate
from app.schemas.enums import JobSource


class LinkedInScraper:
    def __init__(self, keyword="Python"):
        self.keyword = keyword
        self.url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={self.keyword}&location=Ukraine&f_TPR=r604800"  # за последнюю неделю
        )

    async def scrape(self) -> list[VacancyCreate]:
        async with async_playwright() as p:
            print(f"🔗 [LinkedIn] Starting headless browser for: {self.keyword}...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            try:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_selector(
                    ".jobs-search__results-list, ul.jobs-search__results-list",
                    timeout=15000,
                )
            except Exception as e:
                print(f"❌ [LinkedIn] Blocking or timeout: {e}")
                await browser.close()
                return []

            vacancies = []
            items = await page.query_selector_all(".jobs-search__results-list li")
            print(f"🔍 [LinkedIn] Found {len(items)} items, parsing up to 15")

            detail_page = await context.new_page()

            for item in items[:15]:
                try:
                    title_elem = await item.query_selector(".base-search-card__title")
                    company_elem = await item.query_selector(".base-search-card__subtitle")
                    link_elem = await item.query_selector(".base-card__full-link")

                    if not title_elem or not link_elem:
                        continue

                    title = (await title_elem.inner_text()).strip()
                    company = (await company_elem.inner_text()).strip() if company_elem else "Unknown"
                    url = (await link_elem.get_attribute("href") or "").split("?")[0]

                    if not url:
                        continue

                    # Получаем полное описание вакансии
                    description = await self._get_full_description(detail_page, url)

                    vacancies.append(
                        VacancyCreate(
                            title=title,
                            company=company,
                            url=url,
                            description=description or f"{title} at {company}",
                            source=JobSource.LINKEDIN,
                            salary=None,
                        )
                    )
                    print(f"✅ [LinkedIn] Captured: {title}")
                    await asyncio.sleep(2)  # LinkedIn активно блокирует — чуть медленнее

                except Exception as e:
                    print(f"⚠️ [LinkedIn] Error parsing item: {e}")

            await detail_page.close()
            await browser.close()
            return vacancies

    async def _get_full_description(self, page, url: str) -> str:
        """Открывает страницу вакансии LinkedIn и извлекает описание."""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Пробуем развернуть описание (кнопка "See more")
            try:
                see_more = await page.query_selector(
                    "button.show-more-less-html__button--more"
                )
                if see_more:
                    await see_more.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            selectors = [
                ".description__text",
                ".show-more-less-html__markup",
                ".job-description",
                "section.description",
            ]
            for selector in selectors:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 50:
                        return text.strip()[:3000]

        except Exception as e:
            print(f"⚠️ [LinkedIn] Could not get description for {url}: {e}")
        return ""
