import asyncio
import re
from playwright.async_api import async_playwright
from app.schemas.vacancy import VacancyCreate
from app.schemas.enums import JobSource


class DjinniScraper:
    def __init__(self, keyword="Python", exp_level="no", remote=False, city=""):
        self.keyword = keyword
        self.exp_level = exp_level

        url = (
            f"https://djinni.co/jobs/?primary_keyword={keyword}"
            f"&exp_level={exp_level}&sort=date&lang=en"
        )
        if remote:
            url += "&remote=true"
        elif city:
            url += f"&location={city}"

        self.base_url = url

    async def scrape(self) -> list[VacancyCreate]:
        all_vacancies = []

        async with async_playwright() as p:
            print(f"🔗 [Djinni] Starting browser for: {self.keyword}...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            try:
                print(f"📄 [Djinni] Loading: {self.base_url}")
                await page.goto(self.base_url, wait_until="load", timeout=60000)
                await asyncio.sleep(3)

                job_links = await page.query_selector_all(
                    "a[href*='/jobs/'].job-list-item__link, "
                    "a[href*='/jobs/']:not([class*='btn'])"
                )
                print(f"🔍 Found {len(job_links)} job links")

                job_items = []
                for link in job_links:
                    url = await link.get_attribute("href")
                    if not url or "/jobs/" not in url or "view_reviews" in url:
                        continue
                    if url.startswith("/"):
                        url = f"https://djinni.co{url}"
                    url = url.split("?")[0]

                    if not re.search(r"/jobs/\d+", url):
                        continue

                    title = (await link.inner_text()).strip()
                    title = title.split("\n")[0].strip()
                    if not title:
                        continue

                    company = await page.evaluate(
                        """(el) => {
                            let parent = el.closest('li, div.job-list-item, article');
                            if (!parent) return 'Private';
                            let comp = parent.querySelector('a[href*="/company/"]');
                            return comp ? comp.innerText.trim() : 'Private';
                        }""",
                        link,
                    )

                    salary = await page.evaluate(
                        """(el) => {
                            let parent = el.closest('li, div.job-list-item, article');
                            if (!parent) return null;
                            let s = parent.querySelector('.public-salary-item, .job-list-item__salary');
                            return s ? s.innerText.trim() : null;
                        }""",
                        link,
                    )

                    job_items.append({
                        "url": url,
                        "title": title,
                        "company": company.strip(),
                        "salary": salary,
                    })

                seen = set()
                unique_items = []
                for item in job_items:
                    if item["url"] not in seen:
                        seen.add(item["url"])
                        unique_items.append(item)

                print(f"📋 [Djinni] Unique vacancies to parse: {len(unique_items)}")

                detail_page = await context.new_page()
                for item in unique_items:
                    description = await self._get_full_description(detail_page, item["url"])
                    all_vacancies.append(
                        VacancyCreate(
                            title=item["title"],
                            company=item["company"],
                            url=item["url"],
                            description=description or item["title"],
                            source=JobSource.DJINNI,
                            salary=item["salary"],
                        )
                    )
                    print(f"✅ [Djinni] Captured: {item['title']}")
                    await asyncio.sleep(1)

                await detail_page.close()

            except Exception as e:
                print(f"❌ [Djinni] Scraping error: {e}")
            finally:
                await browser.close()

        return all_vacancies

    async def _get_full_description(self, page, url: str) -> str:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)

            selectors = [
                ".vacancy-section",
                ".job-post__description",
                "#job-description",
                "article",
            ]
            for selector in selectors:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 50:
                        return text.strip()[:3000]
        except Exception as e:
            print(f"⚠️ [Djinni] Could not get description for {url}: {e}")
        return ""