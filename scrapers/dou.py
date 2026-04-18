import httpx
from bs4 import BeautifulSoup
from app.schemas.vacancy import VacancyCreate
from app.schemas.enums import JobSource


class DOUScraper:
    def __init__(self, keyword="Python", exp="no"):
        self.keyword = keyword
        self.exp = exp

        self.base_url = f"https://jobs.dou.ua/vacancies/?category={self.keyword}"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://jobs.dou.ua/"
        }

    async def scrape(self) -> list[VacancyCreate]:
        print(f"🔎 Searching DOU for: {self.keyword}...")

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
            try:
                response = await client.get(self.base_url)
                if response.status_code != 200:
                    print(f"❌ DOU returned status: {response.status_code}")
                    return []
            except Exception as e:
                print(f"❌ Error connecting to DOU: {e}")
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
                    print(f"✅ DOU parsed: {title}")

                except Exception as e:
                    print(f"⚠️ Error parsing DOU item: {e}")
                    continue

            return vacancies

    async def get_full_description(self, url: str) -> str:
        async with httpx.AsyncClient(headers=self.headers) as client:
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    full_text = soup.select_one("div.l-vacancy") or soup.select_one(".b-typo")
                    return full_text.get_text(strip=True) if full_text else ""
            except:
                pass
        return ""