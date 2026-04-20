from abc import abstractmethod, ABC
from playwright.async_api import async_playwright


class BaseParser(ABC):
    @abstractmethod
    async def scrape(self) -> list:
        pass

    async def get_page_content(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                content = await page.content()
            except Exception as e:
                print(f"[BaseParser] Error loading {url}: {e}")
                content = ""
            finally:
                await browser.close()
            return content
