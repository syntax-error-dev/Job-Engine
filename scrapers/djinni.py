import asyncio
from playwright.async_api import async_playwright
from app.schemas.vacancy import VacancyCreate
from app.schemas.enums import JobSource


class DjinniScraper:
    def __init__(self, keyword="Python", exp_level="no"):
        self.keyword = keyword
        self.exp_level = exp_level
        self.base_url = f"https://djinni.co/jobs/?primary_keyword={keyword}&exp_level={exp_level}&sort=date&lang=en"

    async def scrape(self) -> list[VacancyCreate]:
        all_vacancies = []
        async with async_playwright() as p:
            print(f"🔗 [Djinni] Starting browser for: {self.keyword}...")

            browser = await p.chromium.launch(headless=False)

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                print(f"📄 [Djinni] Loading: {self.base_url}")
                await page.goto(self.base_url, wait_until="load", timeout=60000)

                await asyncio.sleep(5)

                job_links = await page.query_selector_all(
                    "a[href*='/jobs/'].job-list-item__link, a[href*='/jobs/']:not([class*='btn'])")

                print(f"🔍 Found {len(job_links)} job links via broad search")

                for link in job_links:
                    url = await link.get_attribute("href")
                    if not url or '/jobs/' not in url or 'view_reviews' in url:
                        continue

                    if url.startswith('/'): url = f"https://djinni.co{url}"
                    title = await link.inner_text()
                    if not title.strip(): continue

                    company = await page.evaluate('''
                                                  (el) => {
                                                      let parent = el.closest('li, div.job-list-item, article');
                                                      if (!parent) return 'Private';
                                                      let comp = parent.querySelector('a[href*="/company/"]');
                                                      return comp ? comp.innerText : 'Private';
                                                  }
                                                  ''', link)

                    description = await page.evaluate('''
                                                      (el) => {
                                                          let parent = el.closest('li, div.job-list-item, article');
                                                          if (!parent) return '';
                                                          let desc = parent.querySelector('.job-list-item__description, .list-jobs__description, p');
                                                          return desc ? desc.innerText : '';
                                                      }
                                                      ''', link)

                    all_vacancies.append(VacancyCreate(
                        title=title.strip(),
                        company=company.strip(),
                        url=url.split('?')[0],
                        description=description.strip()[:1000],
                        source=JobSource.DJINNI,
                        salary=None
                    ))
                    print(f"✅ Captured: {title.strip()}")

                seen_urls = set()
                unique_vacancies = []
                for v in all_vacancies:
                    if v.url not in seen_urls:
                        unique_vacancies.append(v)
                        seen_urls.add(v.url)

                    return unique_vacancies