import logging
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from app.schemas.vacancy import VacancyCreate
from app.schemas.enums import JobSource
from scrapers.base import BaseParser

logger = logging.getLogger(__name__)

class DOUScraper(BaseParser):
    def __init__(self, keyword="Python", exp="no"):
        super().__init__()
        self.keyword = keyword
        self.exp = exp
        self.base_url = f"https://jobs.dou.ua/vacancies/?category={self.keyword}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://jobs.dou.ua/"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_page(self, client: httpx.AsyncClient, url: str):
        response = await client.get(url)
        response.raise_for_status()
        return response

    async def scrape(self) -> list[VacancyCreate]:
        logger.info("Searching DOU for: %s", self.keyword)

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
            try:
                response = await self.fetch_page(client, self.base_url)
            except httpx.HTTPError as e:
                logger.error("Error connecting to DOU: %s", e)
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select("li.l-vacancy")
            vacancies = []

            for item in items:
                try:
                    title_elem = item.select_one("a.vt")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = title_elem["href"].split("?")[0]
                    company_elem = item.select_one("a.company")
                    company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
                    salary_elem = item.select_one("span.salary")
                    salary = salary_elem.get_text(strip=True) if salary_elem else None
                    desc_elem = item.select_one("div.sh-info")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""

                    vacancies.append(VacancyCreate(
                        title=title,
                        company=company,
                        url=url,
                        description=description,
                        source=JobSource.DOU,
                        salary=salary
                    ))
                except Exception as e:
                    logger.error("Error parsing DOU item: %s", e)
                    continue

            return vacancies

    async def get_full_description(self, url: str) -> str:
        async with httpx.AsyncClient(headers=self.headers) as client:
            try:
                res = await self.fetch_page(client, url)
                soup = BeautifulSoup(res.text, "html.parser")
                full_text = soup.select_one("div.l-vacancy") or soup.select_one(".b-typo")
                return full_text.get_text(strip=True) if full_text else ""
            except httpx.HTTPError as e:
                logger.error("Error fetching description %s: %s", url, e)
        return ""